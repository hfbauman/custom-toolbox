import adsk.core, adsk.fusion, adsk.cam, traceback
import os
import json
import subprocess

# --- CONFIGURATION ---
EXPORT_FORMAT = "step"  # Options: 'step' or 'f3d'
# ---------------------

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_FILE_PATH = os.path.join(REPO_PATH, "tracked_projects.json")

handlers = []

def is_project_tracked(project_name):
    """Reads the JSON config file and checks if the project should be tracked."""
    if not os.path.exists(CONFIG_FILE_PATH):
        # If the config file doesn't exist, default to tracking nothing for safety
        return False
    
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            tracked_list = config.get("tracked_projects", [])
            # Case-insensitive matching to avoid typos knocking it out
            return project_name.lower() in [p.lower() for p in tracked_list]
    except:
        return False

class DocumentSavingHandler(adsk.core.DocumentEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            eventArgs = adsk.core.DocumentEventArgs.cast(args)
            doc = eventArgs.document
            
            # Ensure it's a CAD design and has an associated cloud project
            if doc.products.itemByProductType('DesignProductType') and doc.dataFile:
                project_name = doc.dataFile.parentProject.name
                
                # Check if this specific project is allowed in the JSON config
                if not is_project_tracked(project_name):
                    return # Exit silently; this project is ignored
                
                design = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
                exportMgr = design.exportManager
                
                filename = f"{doc.name}.{EXPORT_FORMAT}"
                output_path = os.path.join(REPO_PATH, filename)
                
                # Export file
                if EXPORT_FORMAT.lower() == "step":
                    options = exportMgr.createSTEPExportOptions(output_path)
                else:
                    options = exportMgr.createFusionArchiveExportOptions(output_path)
                exportMgr.execute(options)
                
                # Run Git commands
                subprocess.run(["git", "add", filename], cwd=REPO_PATH, shell=True)
                subprocess.run(["git", "commit", "-m", f"Auto-commit: Saved {doc.name} (Project: {project_name})"], cwd=REPO_PATH, shell=True)
                subprocess.run(["git", "push"], cwd=REPO_PATH, shell=True)
                
        except:
            pass 

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        
        # Switched to app.documentSaving to evaluate the document state right as save starts
        onSaving = DocumentSavingHandler()
        app.documentSaving.add(onSaving)
        handlers.append(onSaving)
    except:
        if ui: ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    try:
        app = adsk.core.Application.get()
        app.documentSaving.remove(handlers)
    except:
        pass