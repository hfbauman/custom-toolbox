import adsk.core, adsk.fusion, traceback, os, re, json

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_FILE_PATH = os.path.join(REPO_PATH, "tracked_projects.json")

def get_tracked_projects():
    if not os.path.exists(CONFIG_FILE_PATH):
        return []
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            return [p.lower() for p in config.get("tracked_projects", [])]
    except:
        return []

def get_clean_name(doc_name):
    return re.sub(r'\s+v\d+$', '', doc_name, flags=re.IGNORECASE).strip()

def get_folder_path(data_file):
    parts = []
    folder = data_file.parentFolder
    while folder is not None and folder.parentFolder is not None:
        parts.append(folder.name)
        folder = folder.parentFolder
    parts.reverse()
    return os.path.join(*parts) if parts else ""

def export_file(app, data_file, results):
    doc = None
    try:
        doc = app.documents.open(data_file, True)

        if not doc.products.itemByProductType('DesignProductType'):
            doc.close(False)
            return

        project_name = data_file.parentProject.name
        folder_path = get_folder_path(data_file)
        clean_name = get_clean_name(data_file.name)

        output_dir = os.path.join(REPO_PATH, project_name, folder_path)
        os.makedirs(output_dir, exist_ok=True)

        design = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        exportMgr = design.exportManager

        step_path = os.path.join(output_dir, f"{clean_name}.step")
        exportMgr.execute(exportMgr.createSTEPExportOptions(step_path))

        f3d_path = os.path.join(output_dir, f"{clean_name}.f3d")
        exportMgr.execute(exportMgr.createFusionArchiveExportOptions(f3d_path))

        results["success"].append(f"{project_name}/{folder_path}/{clean_name}")
    except:
        results["failed"].append(f"{data_file.name}: {traceback.format_exc()}")
    finally:
        if doc:
            doc.close(False)

def crawl_folder(app, folder, results):
    for i in range(folder.dataFiles.count):
        export_file(app, folder.dataFiles.item(i), results)
    for i in range(folder.dataFolders.count):
        crawl_folder(app, folder.dataFolders.item(i), results)

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        tracked_projects = get_tracked_projects()
        if not tracked_projects:
            ui.messageBox(f"No tracked projects found in:\n{CONFIG_FILE_PATH}")
            return

        results = {"success": [], "failed": []}

        hub = app.data.activeHub
        for i in range(hub.dataProjects.count):
            project = hub.dataProjects.item(i)
            if project.name.lower() not in tracked_projects:
                continue
            crawl_folder(app, project.rootFolder, results)

        summary = f"Export complete.\n\n"
        summary += f"Succeeded ({len(results['success'])}):\n"
        summary += "\n".join(results["success"]) or "None"
        if results["failed"]:
            summary += f"\n\nFailed ({len(results['failed'])}):\n"
            summary += "\n".join(results["failed"])

        ui.messageBox(summary)
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))