import os
import re

translations_ar = {
    "Geospatial Map – AquaMonitor": "الخريطة الجيومكانية – AquaMonitor",
    "Geospatial Center": "المركز الجيومكاني",
    "Network Overview": "نظرة عامة على الشبكة",
    "Healthy": "سليم",
    "Warning": "تحذير",
    "Critical": "حرج",
    "Interactive Map": "خريطة تفاعلية",
    "Select a farm marker to view active telemetry and alerts.": "حدد علامة مزرعة لعرض القياسات عن بعد والتنبيهات النشطة.",
    "Infrastructure Summary": "ملخص البنية التحتية",
    "Total Farms": "إجمالي المزارع",
    "Active Ponds": "الأحواض النشطة",
    "Active Alerts": "التنبيهات النشطة",
    "Farm Name": "اسم المزرعة",
    "Local Weather": "الطقس المحلي",
    "Location": "الموقع",
    "Loading": "جاري التحميل",
    "Humidity": "الرطوبة",
    "Wind Conditions": "حالة الرياح",
    "Direction": "الاتجاه",
    "Gusts:": "هبات الرياح:",
    "Ponds": "الأحواض",
    "Recent Alerts": "التنبيهات الأخيرة",
    "Manage Farm": "إدارة المزرعة",
    "Unknown": "غير معروف",
    "km/h": "كم/س",
    "No ponds configured.": "لم يتم تكوين أحواض.",
    "Normal": "عادي",
    "Fish": "أسماك",
    "All systems clear": "جميع الأنظمة تعمل بشكل جيد",
    "Failed to load payload": "فشل في تحميل البيانات",
    "Map View": "عرض الخريطة"
}

translations_fr = {
    "Geospatial Map – AquaMonitor": "Carte Géospatiale – AquaMonitor",
    "Geospatial Center": "Centre Géospatial",
    "Network Overview": "Aperçu du Réseau",
    "Healthy": "Sain",
    "Warning": "Avertissement",
    "Critical": "Critique",
    "Interactive Map": "Carte Interactive",
    "Select a farm marker to view active telemetry and alerts.": "Sélectionnez un marqueur de ferme pour voir la télémétrie.",
    "Infrastructure Summary": "Résumé de l'Infrastructure",
    "Total Farms": "Total des Fermes",
    "Active Ponds": "Bassins Actifs",
    "Active Alerts": "Alertes Actives",
    "Farm Name": "Nom de la Ferme",
    "Local Weather": "Météo Locale",
    "Location": "Emplacement",
    "Loading": "Chargement...",
    "Humidity": "Humidité",
    "Wind Conditions": "Conditions de Vent",
    "Direction": "Direction",
    "Gusts:": "Rafales:",
    "Ponds": "Bassins",
    "Recent Alerts": "Alertes Récentes",
    "Manage Farm": "Gérer la Ferme",
    "Unknown": "Inconnu",
    "km/h": "km/h",
    "No ponds configured.": "Aucun bassin configuré.",
    "Normal": "Normal",
    "Fish": "poissons",
    "All systems clear": "Tous les systèmes sont normaux",
    "Failed to load payload": "Échec du chargement",
    "Map View": "Vue Carte"
}

def process_po(filepath, mapping):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = re.split(r'\n{2,}', content)
    unique_blocks = {}
    ordered_ids = []
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        match = re.search(r'^msgid "(.*?)"', block, re.MULTILINE)
        if match:
            msgid = match.group(1)
            if msgid not in unique_blocks:
                unique_blocks[msgid] = block
                ordered_ids.append(msgid)
            else:
                # Keep the block that has location comments over the manual ones
                if '#:' in block:
                    unique_blocks[msgid] = block
        else:
            if '__header__' not in unique_blocks:
                unique_blocks['__header__'] = block
                ordered_ids.insert(0, '__header__')
            else:
                # Append to header just in case
                unique_blocks['__header__'] += "\n\n" + block

    for msgid in ordered_ids:
        if msgid in mapping:
            target_str = mapping[msgid]
            block = unique_blocks[msgid]
            # Strip out any existing msgstr line(s) and replace them cleanly
            # Regex to find msgstr line and anything following inside quotes
            block = re.sub(r'msgstr\s+(".*")(\n".*")*', f'msgstr "{target_str}"', block)
            unique_blocks[msgid] = block

    with open(filepath, 'w', encoding='utf-8') as f:
        for msgid in ordered_ids:
            # Reconstruct the PO file
            f.write(unique_blocks[msgid] + "\n\n")

process_po("locale/ar/LC_MESSAGES/django.po", translations_ar)
process_po("locale/fr/LC_MESSAGES/django.po", translations_fr)

print("PO files cleaned, deduplicated, and accurately injected!")
