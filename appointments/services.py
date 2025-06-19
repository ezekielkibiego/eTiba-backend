from django.utils import timezone
from datetime import datetime, timedelta, time, timezone as dt_timezone # Import time and Python's timezone
from doctors.models import Doctor, DoctorAvailability, DoctorUnavailability # Import Doctor
from .models import Appointment

class AppointmentService:

    # Assuming appointment_datetime is timezone-aware (e.g., UTC) when passed to this method
    @staticmethod
    def is_doctor_available(doctor, appointment_datetime, duration_minutes, appointment_id=None):
        """
        Checks if a doctor is available for a given datetime and duration.
        Considers DoctorAvailability, DoctorUnavailability, and existing Appointments.
        `appointment_id` is used to exclude the current appointment when checking for updates.
        """
        local_tz = timezone.get_current_timezone()
        
        # Convert the proposed UTC appointment_datetime to local time for schedule checks
        appointment_datetime_local = appointment_datetime.astimezone(local_tz)
        
        day_of_week_local = appointment_datetime_local.weekday()
        appointment_time_local = appointment_datetime_local.time()
        appointment_end_time_local = (appointment_datetime_local + timedelta(minutes=duration_minutes)).time()
        appointment_date_local = appointment_datetime_local.date()

        # 1. Check against Doctor's general availability schedule (local time based)
        try:
            availability_slot = DoctorAvailability.objects.get(
                doctor=doctor, day_of_week=day_of_week_local, is_active=True,
                start_time__lte=appointment_time_local, 
                end_time__gte=appointment_end_time_local # Slot must fit within working hours
            )
            # Check for breaks
            if availability_slot.break_start and availability_slot.break_end:
                # Proposed slot overlaps with break if: (proposed_start < break_end) and (proposed_end > break_start)
                if appointment_time_local < availability_slot.break_end and \
                   appointment_end_time_local > availability_slot.break_start:
                    return False # Conflicts with break
        except DoctorAvailability.DoesNotExist:
            return False # No general availability slot for this day/time

        # 2. Check against DoctorUnavailability (local date based)
        if DoctorUnavailability.objects.filter(
            doctor=doctor, 
            start_date__lte=appointment_date_local, 
            end_date__gte=appointment_date_local
        ).exists():
            return False

        # 3. Check against existing appointments for conflicts (UTC based)
        # appointment_datetime is already UTC. appt.appointment_datetime from DB is also UTC.
        new_appointment_end_utc = appointment_datetime + timedelta(minutes=duration_minutes)

        conflicting_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_datetime__lt=new_appointment_end_utc,  # existing_start < new_end
            status__in=['scheduled', 'confirmed', 'in_progress'] # Consider relevant statuses
        ).exclude(pk=appointment_id if appointment_id else None) # Exclude current appointment if updating
        
        for appt in conflicting_appointments:
            existing_appt_end_utc = appt.appointment_datetime + timedelta(minutes=appt.duration)
            # Overlap if: (new_start < existing_end) and (new_end > existing_start)
            if appointment_datetime < existing_appt_end_utc and new_appointment_end_utc > appt.appointment_datetime:
                return False # Overlap detected

        return True

    @staticmethod
    def get_available_slots(doctor_id, date_obj: datetime.date, duration_minutes: int = 30):
        """
        Returns a list of available time slots (HH:MM strings in local time)
        for a doctor on a specific date.
        """
        try:
            doctor = Doctor.objects.get(pk=doctor_id)
        except Doctor.DoesNotExist:
            return []

        day_of_week = date_obj.weekday()
        local_tz = timezone.get_current_timezone()

        try:
            schedule = DoctorAvailability.objects.get(doctor=doctor, day_of_week=day_of_week, is_active=True)
        except DoctorAvailability.DoesNotExist:
            return []

        if DoctorUnavailability.objects.filter(doctor=doctor, start_date__lte=date_obj, end_date__gte=date_obj).exists():
            return []

        query_start_utc = timezone.make_aware(datetime.combine(date_obj, time.min), local_tz).astimezone(dt_timezone.utc)
        query_end_utc = timezone.make_aware(datetime.combine(date_obj + timedelta(days=1), time.min), local_tz).astimezone(dt_timezone.utc)

        booked_appts_qs = Appointment.objects.filter(
            doctor=doctor,
            appointment_datetime__gte=query_start_utc,
            appointment_datetime__lt=query_end_utc,
            status__in=['scheduled', 'confirmed', 'in_progress']
        )

        booked_local_naive_ranges = []
        for appt in booked_appts_qs:
            start_local = appt.appointment_datetime.astimezone(local_tz)
            end_local = (appt.appointment_datetime + timedelta(minutes=appt.duration)).astimezone(local_tz)
            if start_local.date() == date_obj or end_local.date() == date_obj: # Ensure it affects the target day
                booked_local_naive_ranges.append(
                    (start_local.replace(tzinfo=None), end_local.replace(tzinfo=None))
                )

        available_slots_str = []
        current_time_naive = datetime.combine(date_obj, schedule.start_time)
        working_end_naive = datetime.combine(date_obj, schedule.end_time)

        break_start_naive = datetime.combine(date_obj, schedule.break_start) if schedule.break_start else None
        break_end_naive = datetime.combine(date_obj, schedule.break_end) if schedule.break_end else None

        while True:
            slot_start_naive = current_time_naive
            slot_end_naive = slot_start_naive + timedelta(minutes=duration_minutes)

            if slot_end_naive > working_end_naive:
                break

            is_slot_free = True

            # Check break
            if break_start_naive and break_end_naive:
                if slot_start_naive < break_end_naive and slot_end_naive > break_start_naive:
                    is_slot_free = False
            
            # Check booked appointments
            if is_slot_free:
                for booked_start, booked_end in booked_local_naive_ranges:
                    if slot_start_naive < booked_end and slot_end_naive > booked_start:
                        is_slot_free = False
                        break
            
            if is_slot_free:
                available_slots_str.append(slot_start_naive.strftime("%H:%M"))

            current_time_naive += timedelta(minutes=duration_minutes) # Assuming slots are contiguous by duration

        return available_slots_str