from asyncio import events
from math import floor
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.contrib import messages
import io
import calendar
import csv

# from requests import request

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from calendar import HTMLCalendar
from datetime import datetime
from .models import Event, MyClubUser, Venue
from .forms import VenueForm, EventForm, AdminEventForm

# Create your views here.
def venue_text(request):
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="venue.txt"'
    
    venues = Venue.objects.all()
    lines = []
    for venue in venues:
        lines.append(f"Venue Name : {venue}\n Venue Address : {venue.address}, {venue.zip_code}\n Contact Detail : {venue.phone}\n Website : {venue.web}\n Email Address : {venue.email_address}\n\n\n")
    response.writelines(lines)
    return response

#Show Event
def show_events(request,event_id):
    event = Event.objects.get(pk=event_id)
    return render(request,'events/show_event.html',{"event":event})

#Show Events In A Venue
def venue_events(request,venue_id):
    venue = Venue.objects.get(id=venue_id)
    events = venue.event_set.all()
    if events:
        return render(request,'events/venue_event.html',{"events":events})
    else:
        messages.success(request,('That venue has no events.'))
        return redirect('admin_approval')

def venue_csv(request):
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="venue.csv"'

    writer = csv.writer(response)
    venues = Venue.objects.all()
    writer.writerow(['Venue Name', 'Venue Address', 'Venue Zip Code', 'Contact Detail', 'Website', 'Email Address'])

    for venue in venues:
        writer.writerow([venue,venue.address,venue.zip_code,venue.phone,venue.web,venue.email_address])
    return response


def venue_pdf(request):
    # Create Bytestream buffer
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, bottomup=0)
    textobj = c.beginText()
    textobj.setTextOrigin(inch, inch)
    textobj.setFont("Helvetica", 14)

    venues = Venue.objects.all()
    lines=[]

    for venue in venues:
        lines.append(venue.name)
        lines.append(venue.address)
        lines.append(venue.zip_code)
        lines.append(venue.phone)
        lines.append(venue.web)
        lines.append(venue.email_address)
        lines.append("  ")

    for line in lines:
        textobj.textLine(line)
    
    c.drawText(textobj)
    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename='venue.pdf')


def admin_approval(request):
    # Get the venue List
    venue_list = Venue.objects.all()
    # Get counts
    event_count = Event.objects.all().count()
    venue_count = Venue.objects.all().count()
    user_count = User.objects.all().count()

    event_list = Event.objects.all().order_by('-event_date')
    if request.user.is_superuser:
        if request.method == 'POST':
            id_list = request.POST.getlist('boxes')
            event_list.update(approved=False)
            for id in id_list:
                Event.objects.filter(pk=int(id)).update(approved=True)
            messages.success(request,('Event List Approval has been updated!!'))
            return redirect('list-events')
        else:
           return render(request, 'events/admin_approval.html', {"event_list": event_list, "event_count": event_count, "venue_count": venue_count, "user_count": user_count,"venue_list":venue_list})
    else:
        messages.success(request,('You are not allowed to access this Page'))
        return redirect('home')



def my_events(request):
    if request.user.is_authenticated:
        me = request.user.id
        events = Event.objects.filter(attendees=me)
        return render(request, 'events/my_events.html', {"events": events})
    else:
        messages.success(request, "Your are not authorised to view this page.")
        return redirect('home')


def update_venue(request, venue_id):
    venue = Venue.objects.get(pk=venue_id)
    form = VenueForm(request.POST or None, instance=venue)
    if form.is_valid():
        form.save()
        return redirect('list-venues')
    return render(request, 'events/update_venue.html', {"venue": venue, "form": form})


def update_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.user.is_superuser:
        form = AdminEventForm(request.POST or None, instance=event)
    else:
        form = EventForm(request.POST or None, instance=event)
    if form.is_valid():
        form.save()
        return redirect('list-events')
    return render(request, 'events/update_event.html', {"event": event, "form": form})


@csrf_exempt
def search_venue(request):
    if request.method == 'POST':
        searched = request.POST['searched']
        venues = Venue.objects.filter(name__contains=searched)
        return render(request, 'events/search_venues.html', {"searched":searched, "venues":venues})
    else:
        return render(request, 'events/search_venues.html', {})


def search_event(request):
    if request.method == 'POST':
        searched = request.POST['searched']
        events = Event.objects.filter(name__contains=searched)
        return render(request, 'events/search_events.html', {"searched":searched, "events":events})
    else:
        return render(request, 'events/search_events.html', {})


def show_venue(request, venue_id):
    venue = Venue.objects.get(pk=venue_id)
    venue_owner = User.objects.get(pk=venue.owner)

    events = venue.event_set.all()
    return render(request, 'events/show_venue.html', {"venue": venue, "venue_owner": venue_owner,"events":events})


def list_venues(request):
    venue_list = Venue.objects.all().order_by('-name')
    paginator = Paginator(venue_list, 2)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    num_page = "a" * page_obj.paginator.num_pages
    return render(request, 'events/venue_list.html', {"page_obj": page_obj, "num_page": num_page})


def add_venue(request):
    submitted = False
    if request.method == 'POST':
        form = VenueForm(request.POST)
        if form.is_valid():
            venue = form.save(commit=False)
            venue.owner = request.user.id  # Logged in user
            venue.save()
            return HttpResponseRedirect('/add_venue?submitted=True')
    else:
        form = VenueForm
        if 'submitted' in request.GET:
            submitted = True
    return render(request, 'events/add_venue.html', {"form":form, "submitted":submitted})


def add_event(request):
    submitted = False
    if request.method == 'POST':
        if request.user.is_superuser:
            form = AdminEventForm(request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect('/add_event?submitted=True')   
        else:
            form = AdminEventForm(request.POST)
            if form.is_valid():
                event = form.save(commit=False)
                event.manager = request.user  # Logged in user
                event.save()
                return HttpResponseRedirect('/add_event?submitted=True')
    else:
        if request.user.is_superuser:
            form = AdminEventForm
        else:
            form = EventForm
        if 'submitted' in request.GET:
            submitted = True
    return render(request, 'events/add_event.html', {"form":form, "submitted":submitted})


def delete_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.user == event.manager:
        event.delete()
        messages.success(request, "Event deleted successfully..")
        return redirect('list-events')
    else:
        messages.success(request, "You aren't authorized to delete th event.")
        return redirect('list-events')


def delete_venue(request, venue_id):
    venue = Venue.objects.get(pk=venue_id)
    venue.delete()
    return redirect('list-venues')


def all_events(request):
    event_list  = Event.objects.all().order_by('event_date')
    paginator = Paginator(event_list, 2)
    club_user = MyClubUser.objects.all().count()
    attend_count=[i.attendees.all().count() for i in event_list][-1]
    
    attendence_percentage=round((attend_count/club_user)*100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    num_page = "a" * page_obj.paginator.num_pages
    return render(request, 'events/event_list.html', {"page_obj": page_obj, "num_page": num_page,"attendence_percentage":attendence_percentage})


def home(request, year=datetime.now().year, month=datetime.now().strftime('%B')):
    month = month.title()

    # Convert month from name to number
    month_number = list(calendar.month_name).index(month)
    month_number = int(month_number)

    # Get Current Year
    now = datetime.now()
    current_year = now.year

    # Query the Events Model for Dates
    event_list = Event.objects.filter(event_date__year=datetime.now().year, event_date__month=month_number).order_by('event_date')

    # Get Current Time
    time = now.strftime("%I:%M:%S %p")

    # Create a calendar
    cal = HTMLCalendar().formatmonth(year, month_number)
    return render(request, 'events/home.html', {"year": year, "month": month, "month_number": month_number, "cal": cal, "current_year": current_year, "time":time, "event_list": event_list})
