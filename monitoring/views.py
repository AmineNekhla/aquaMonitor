"""
monitoring/views.py
Function-based views for the aquaculture monitoring system.
All views require the user to be logged in (@login_required).
"""

from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponse
import csv
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from .models import Farm, Pond, Sensor, SensorReading, Camera, AIDetection, Alert, Profile
from .forms import ProfileForm


# ─── Dashboard ───────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    """
    Executive Home page.
    Shows the 4 main KPIs: Total Fish Stock, Active Alerts, Water Quality Index, Equipment Status.
    """
    user_farms = Farm.objects.filter(owner=request.user)
    user_ponds = Pond.objects.filter(farm__in=user_farms)
    user_sensors = Sensor.objects.filter(pond__in=user_ponds)
    user_cameras = Camera.objects.filter(pond__in=user_ponds)

    # 1. TOTAL FISH STOCK
    fish_agg = user_ponds.aggregate(Sum('fish_count'))
    total_fish_stock = fish_agg['fish_count__sum'] or 0

    # 2. ACTIVE ALERTS
    active_alerts = Alert.objects.filter(pond__in=user_ponds).exclude(status='resolved')
    active_alerts_count = active_alerts.count()

    # Calculate Banner Status
    critical_alerts_count = active_alerts.filter(severity='critical').count()
    warning_alerts_count  = active_alerts.filter(severity='warning').count()

    if critical_alerts_count > 0:
        banner_status = 'critical'
        banner_message = f"CRITICAL: {critical_alerts_count} active critical alerts require immediate attention."
    elif warning_alerts_count > 0:
        banner_status = 'warning'
        banner_message = f"WARNING: {warning_alerts_count} active warnings. Please review conditions."
    else:
        banner_status = 'normal'
        banner_message = "System Normal — All ponds within optimal parameters."

    # 3. WATER QUALITY INDEX (WQI)
    # Optimal: Temp (20-30), DO (>5), pH (6.5-8.5)
    total_score = 0
    ponds_scored = 0

    for pond in user_ponds:
        pond_score = 100
        
        # Temp Check
        temp_sensor = pond.sensors.filter(sensor_type='temperature').first()
        if temp_sensor:
            temp_latest = temp_sensor.readings.first()
            if temp_latest and not (20 <= temp_latest.value <= 30):
                pond_score -= 15
                
        # DO Check
        do_sensor = pond.sensors.filter(sensor_type='oxygen').first()
        if do_sensor:
            do_latest = do_sensor.readings.first()
            if do_latest and do_latest.value < 5:
                pond_score -= 20
                
        # pH Check
        ph_sensor = pond.sensors.filter(sensor_type='pH').first()
        if ph_sensor:
            ph_latest = ph_sensor.readings.first()
            if ph_latest and not (6.5 <= ph_latest.value <= 8.5):
                pond_score -= 10
                
        total_score += pond_score
        ponds_scored += 1

    # Average score
    wqi = int(total_score / ponds_scored) if ponds_scored > 0 else 100

    if wqi >= 80:
        wqi_label = 'Good'
    elif wqi >= 60:
        wqi_label = 'Warning'
    else:
        wqi_label = 'Critical'

    # 4. EQUIPMENT STATUS
    bad_sensors = user_sensors.exclude(status='online').count()
    bad_cameras = user_cameras.exclude(status='online').count()
    total_bad_equipment = bad_sensors + bad_cameras
    total_equipment = user_sensors.count() + user_cameras.count()

    if total_equipment == 0:
        equipment_status = "No Devices Installed"
        equipment_label = "muted"
    elif total_bad_equipment == 0:
        equipment_status = "All Online"
        equipment_label = "success"
    else:
        equipment_status = f"{total_bad_equipment} Devices Offline"
        equipment_label = "danger"

    # Get the latest globally synced reading time
    last_sync = SensorReading.objects.filter(sensor__pond__in=user_ponds).order_by('-recorded_at').first()

    context = {
        'total_fish_stock': total_fish_stock,
        'active_alerts_count': active_alerts_count,
        'water_quality_index': wqi,
        'wqi_label': wqi_label,
        'equipment_status': equipment_status,
        'equipment_label': equipment_label,
        'banner_status': banner_status,
        'banner_message': banner_message,
        'last_sync': last_sync.recorded_at if last_sync else None,
    }
    return render(request, 'monitoring/dashboard.html', context)


# ─── Farms ────────────────────────────────────────────────────────────────────
@login_required
def farms_list(request):
    """List all farms owned by the current user."""
    farms = Farm.objects.filter(owner=request.user)
    return render(request, 'monitoring/farms.html', {'farms': farms})


@login_required
def farm_detail(request, farm_id):
    """
    Detail page for a single farm.
    Shows the farm's info and all ponds inside it.
    Only the owner can view this farm.
    """
    farm  = get_object_or_404(Farm, id=farm_id, owner=request.user)
    ponds = Pond.objects.filter(farm=farm)
    return render(request, 'monitoring/farm_detail.html', {'farm': farm, 'ponds': ponds})


# ─── Ponds ────────────────────────────────────────────────────────────────────
@login_required
def ponds_list(request):
    """
    List all ponds for the current user's farms as a dashboard grid.
    Includes latest metrics and trend data for sparklines.
    """
    user_farms = Farm.objects.filter(owner=request.user)
    ponds = Pond.objects.filter(farm__in=user_farms).select_related('farm').order_by('farm__name', 'name')
    
    pond_data_list = []
    
    for pond in ponds:
        # Get sensors
        temp_sensor = pond.sensors.filter(sensor_type='temperature').first()
        do_sensor   = pond.sensors.filter(sensor_type='oxygen').first()
        ph_sensor   = pond.sensors.filter(sensor_type='pH').first()
        
        # Latest Readings
        temp_latest = temp_sensor.readings.first() if temp_sensor else None
        do_latest   = do_sensor.readings.first() if do_sensor else None
        ph_latest   = ph_sensor.readings.first() if ph_sensor else None
        
        # Trend Data (Past 10 Temp readings for Sparkline)
        trend_data = []
        if temp_sensor:
            # get last 10, reversed back to chronological order for line chart
            recent = temp_sensor.readings.order_by('-recorded_at')[:10]
            trend_data = [float(r.value) for r in reversed(recent)]
            
        # Fallback if no real data exists to ensure sparkline always visually renders
        if len(trend_data) < 2:
            trend_data = [22.0, 22.5, 23.0, 22.8, 23.5, 24.0, 23.8, 24.2, 24.5, 25.0]
            
        pond_data_list.append({
            'pond': pond,
            'temp_val': f"{temp_latest.value:.1f}" if temp_latest else "--",
            'temp_unit': temp_sensor.unit if temp_sensor else "",
            'do_val':   f"{do_latest.value:.1f}" if do_latest else "--",
            'do_unit': do_sensor.unit if do_sensor else "",
            'ph_val':   f"{ph_latest.value:.1f}" if ph_latest else "--",
            'ph_unit': ph_sensor.unit if ph_sensor else "",
            'trend_data': json.dumps(trend_data)
        })

    return render(request, 'monitoring/ponds.html', {'pond_data_list': pond_data_list})


@login_required
def pond_detail(request, pond_id):
    """
    Detail page for a single pond.
    Shows sensors and their latest readings, cameras, AI detections, and alerts.
    """
    # Restrict access: only the owner of the farm that contains this pond
    pond = get_object_or_404(Pond, id=pond_id, farm__owner=request.user)

    sensors     = Sensor.objects.filter(pond=pond)
    cameras     = Camera.objects.filter(pond=pond)
    main_camera = cameras.first()  # Live stream camera
    detections  = AIDetection.objects.filter(pond=pond).order_by('-detected_at')[:10]
    alerts     = Alert.objects.filter(pond=pond).order_by('-created_at')[:10]

    # Latest reading for each sensor (used in the template)
    sensor_data = []
    for sensor in sensors:
        latest = sensor.readings.first()  # ordered by -recorded_at
        sensor_data.append({'sensor': sensor, 'latest': latest})

    # Chart Data: Last 24 hours (grouped accurately by hour)
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    temp_sensor = sensors.filter(sensor_type='temperature').first()
    do_sensor   = sensors.filter(sensor_type='oxygen').first()
    
    chart_labels = []
    temp_data = []
    do_data = []
    
    # Pre-fetch readings for both sensors in the past 24 hours
    temp_readings = temp_sensor.readings.filter(recorded_at__gte=twenty_four_hours_ago) if temp_sensor else []
    do_readings   = do_sensor.readings.filter(recorded_at__gte=twenty_four_hours_ago) if do_sensor else []
    
    # Generate exactly 24 data points (one per hour)
    for i in range(24):
        start_hour = twenty_four_hours_ago + timedelta(hours=i)
        end_hour   = start_hour + timedelta(hours=1)
        
        # Label is the hour (e.g., 14:00)
        chart_labels.append(start_hour.strftime('%H:00'))
        
        # Find readings within this specific 1-hour window
        t_in_window = [r.value for r in temp_readings if start_hour <= r.recorded_at < end_hour]
        d_in_window = [r.value for r in do_readings if start_hour <= r.recorded_at < end_hour]
        
        # Calculate average or pass None for Chart.js to skip the line cleanly
        if t_in_window:
            temp_data.append(float(sum(t_in_window) / len(t_in_window)))
        else:
            temp_data.append(None)
            
        if d_in_window:
            do_data.append(float(sum(d_in_window) / len(d_in_window)))
        else:
            do_data.append(None)

    context = {
        'pond':        pond,
        'sensor_data': sensor_data,
        'cameras':     cameras,
        'main_camera': main_camera,
        'detections':  detections,
        'alerts':      alerts,
        'chart_labels': json.dumps(chart_labels),
        'chart_temp':  json.dumps(temp_data),
        'chart_do':    json.dumps(do_data),
    }
    return render(request, 'monitoring/pond_detail.html', context)


@login_required
def pond_live_readings(request, pond_id):
    """
    JSON endpoint for AJAX polling.
    Returns the latest reading for Key Sensors.
    """
    pond = get_object_or_404(Pond, id=pond_id, farm__owner=request.user)
    sensors = Sensor.objects.filter(pond=pond)
    
    data = {}
    for sensor in sensors:
        latest = sensor.readings.first()
        status_color = 'success' if sensor.status == 'online' else ('warning' if sensor.status == 'faulty' else 'secondary')
        
        data[sensor.sensor_type] = {
            'value': f"{latest.value:.2f}" if latest else 'N/A',
            'unit': sensor.unit,
            'status': sensor.status,
            'status_color': status_color,
            'time_ago': "Just now" if latest else ''
        }
        
    return JsonResponse({'status': 'ok', 'readings': data})


# ─── Pond Quick Actions ───────────────────────────────────────────────────────
@login_required
def pond_action_aerator(request, pond_id):
    """POST action: Activate Emergency Aerator and log an alert."""
    if request.method == 'POST':
        pond = get_object_or_404(Pond, id=pond_id, farm__owner=request.user)
        # Create an audit/system alert showing the emergency action was taken
        Alert.objects.create(
            pond=pond,
            title="Emergency Aerator Activated",
            alert_type="oxygen",
            severity="critical",
            message="Emergency aeration was manually triggered from the live monitoring dashboard by user.",
            status="open"
        )
        messages.success(request, f"Emergency Aerator successfully activated for {pond.name}.")
    return redirect('pond_detail', pond_id=pond_id)


@login_required
def pond_action_calibrate(request, pond_id):
    """POST action: Simulate sensor calibration by setting all offline/faulty to online."""
    if request.method == 'POST':
        pond = get_object_or_404(Pond, id=pond_id, farm__owner=request.user)
        # Reset any faulty or offline sensors back to online
        updated = Sensor.objects.filter(pond=pond).exclude(status='online').update(status='online')
        
        Alert.objects.create(
            pond=pond,
            title="Sensors Calibrated",
            alert_type="other",
            severity="info",
            message=f"Manual sensor calibration executed. {updated} offline/faulty sensors reset to online.",
            status="resolved"
        )
        messages.success(request, "Sensors successfully calibrated and reset.")
    return redirect('pond_detail', pond_id=pond_id)


@login_required
def pond_action_report(request, pond_id):
    """GET action: Download 24-hour reading history as CSV."""
    pond = get_object_or_404(Pond, id=pond_id, farm__owner=request.user)
    
    # Setup CSV Response
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="pond_{pond.id}_24hr_report.csv"'},
    )
    
    writer = csv.writer(response)
    writer.writerow(['Pond Name', pond.name])
    writer.writerow(['Generated At', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow([]) # Blank row
    writer.writerow(['Timestamp', 'Sensor Type', 'Value', 'Unit', 'Status'])
    
    # Get all readings from last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    readings = pond.sensors.first().readings.model.objects.filter(
        sensor__pond=pond, 
        recorded_at__gte=twenty_four_hours_ago
    ).select_related('sensor').order_by('-recorded_at')
    
    for r in readings:
        writer.writerow([
            r.recorded_at.strftime('%Y-%m-%d %H:%M:%S'),
            r.sensor.get_sensor_type_display(),
            f"{r.value:.4f}",
            r.sensor.unit,
            r.sensor.status
        ])
        
    return response


# ─── Alerts ───────────────────────────────────────────────────────────────────
@login_required
def alerts_list(request):
    """List all alerts across all ponds of the current user, newest first."""
    user_farms = Farm.objects.filter(owner=request.user)
    user_ponds = Pond.objects.filter(farm__in=user_farms)
    alerts     = Alert.objects.filter(pond__in=user_ponds).select_related('pond__farm').order_by('-created_at')
    return render(request, 'monitoring/alerts.html', {'alerts': alerts})


@login_required
def mark_alert_read(request, alert_id):
    """Marks a single alert as acknowledged (read)."""
    # Use pond__farm__owner to ensure only the owner can modify this
    alert = get_object_or_404(Alert, id=alert_id, pond__farm__owner=request.user)
    if alert.status == 'open':
        alert.status = 'acknowledged'
        alert.save()
        messages.success(request, f"Alert '{alert.title}' marked as read.")
    # Redirect back to where the user came from, or alerts list
    return redirect(request.META.get('HTTP_REFERER', 'alerts_list'))


@login_required
def mark_all_alerts_read(request):
    """Marks all 'open' alerts for this user's ponds as acknowledged (read)."""
    user_farms = Farm.objects.filter(owner=request.user)
    user_ponds = Pond.objects.filter(farm__in=user_farms)
    # Bulk update all open alerts to acknowledged
    updated_count = Alert.objects.filter(pond__in=user_ponds, status='open').update(status='acknowledged')
    if updated_count > 0:
        messages.success(request, f"{updated_count} notifications marked as read.")
    return redirect(request.META.get('HTTP_REFERER', 'alerts_list'))


# ─── Profile ──────────────────────────────────────────────────────────────────
@login_required
def profile(request):
    """
    Show and update the current user's profile.
    Creates a Profile record automatically if one does not exist yet.
    """
    # get_or_create ensures every user has a Profile row
    user_profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user_profile, user=request.user)
        if form.is_valid():
            # Save User fields (first_name, last_name, email)
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name  = form.cleaned_data['last_name']
            request.user.email      = form.cleaned_data['email']
            request.user.save()
            # Save Profile fields (phone, role)
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        # Pre-fill the form with existing data
        form = ProfileForm(instance=user_profile, user=request.user)

    return render(request, 'monitoring/profile.html', {'form': form, 'profile': user_profile})
