import adsk.core, adsk.fusion, traceback, os, subprocess, re

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GIT_PATH = r"C:\Program Files\Git\bin\git.exe"

handlers = []

def get_fusion_folder_path(data_file):
    parts = []
    folder = data_file.parentFolder
    while folder is not None and folder.parentFolder is not None:
        parts.append(folder.name)
        folder = folder.parentFolder
    parts.reverse()
    return os.path.join(*parts) if parts else ""

def get_clean_name(doc_name):
        # Strip Fusion360's version suffix, e.g. "Drawer Reinforcement v8" -> "Drawer Reinforcement"
        return re.sub(r'\s+v\d+$', '', doc_name, flags=re.IGNORECASE).strip()

class DocumentSavedHandler(adsk.core.DocumentEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            doc = adsk.core.DocumentEventArgs.cast(args).document

            if not (doc.products.itemByProductType('DesignProductType') and doc.dataFile):
                return

            project_name = doc.dataFile.parentProject.name
            folder_path = get_fusion_folder_path(doc.dataFile)

            output_dir = os.path.join(REPO_PATH, project_name, folder_path)
            os.makedirs(output_dir, exist_ok=True)

            clean_name = get_clean_name(doc.name)
            design = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
            exportMgr = design.exportManager

            # Export STEP
            step_filename = f"{clean_name}.step"
            step_path = os.path.join(output_dir, step_filename)
            step_relative = os.path.join(project_name, folder_path, step_filename)
            exportMgr.execute(exportMgr.createSTEPExportOptions(step_path))

            # Export Fusion native (.f3d)
            f3d_filename = f"{clean_name}.f3d"
            f3d_path = os.path.join(output_dir, f3d_filename)
            f3d_relative = os.path.join(project_name, folder_path, f3d_filename)
            exportMgr.execute(exportMgr.createFusionArchiveExportOptions(f3d_path))

            # Commit both files in a single commit
            subprocess.run([GIT_PATH, "add", step_relative, f3d_relative], cwd=REPO_PATH, check=True)
            subprocess.run([GIT_PATH, "commit", "-m", doc.name], cwd=REPO_PATH, check=True)

            ui.messageBox(f"Committed: {doc.name}")
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        onSaved = DocumentSavedHandler()
        app.documentSaved.add(onSaved)
        handlers.append(onSaved)

        ui.messageBox("GitAutoCommit is running — it will export and commit on every save.")
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    try:
        app = adsk.core.Application.get()
        for handler in handlers:
            app.documentSaved.remove(handler)
        handlers.clear()
    except:
        pass