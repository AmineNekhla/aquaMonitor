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

def fill_po(filepath, mapping):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (Not found)")
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    for msgid, msgstr_val in mapping.items():
        safe_msgid = re.escape(msgid)
        # Matches strictly if the translation is completely empty
        pattern = f'(msgid "{safe_msgid}"\\nmsgstr )""'
        replacement = f'\\1"{msgstr_val}"'
        content = re.sub(pattern, replacement, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
fill_po("locale/ar/LC_MESSAGES/django.po", translations_ar)
fill_po("locale/fr/LC_MESSAGES/django.po", translations_fr)
print("Safely injected missing UI strings via regex.")
