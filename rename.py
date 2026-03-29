import os
import glob

files = glob.glob(r"c:\Users\amine\OneDrive\Desktop\aqua\aquaMonitor\monitoring\templates\monitoring\*.html")
files.append(r"c:\Users\amine\OneDrive\Desktop\aqua\aquaMonitor\translate_po.py")
files.append(r"c:\Users\amine\OneDrive\Desktop\aqua\aquaMonitor\walkthrough.md")
files.append(r"c:\Users\amine\OneDrive\Desktop\aqua\aquaMonitor\task.md")

for file in files:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = content.replace("AquaPulse", "AquaMonitor")
        
        if new_content != content:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {file}")
