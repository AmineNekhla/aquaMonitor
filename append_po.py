import os

PO_PATH = "locale/ar/LC_MESSAGES/django.po"

translations = {
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

with open(PO_PATH, 'a', encoding='utf-8') as f:
    f.write("\n\n")
    for msgid, msgstr in translations.items():
        f.write(f'msgid "{msgid}"\n')
        f.write(f'msgstr "{msgstr}"\n\n')

print("Successfully injected Arabic translations into django.po!")
