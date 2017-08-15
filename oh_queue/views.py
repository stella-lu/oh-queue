import datetime
import dateutil.parser
import functools
import collections
import pytz

from flask import render_template, url_for
from flask_login import current_user
from flask_socketio import emit

from oh_queue import app, calendar, db, socketio
from oh_queue.models import Ticket, TicketStatus, TicketEvent, TicketEventType

def user_json(user):
    return {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'shortName': user.short_name,
        'isStaff': user.is_staff,
        'creditBalance': user.credit_balance,
    }

def student_json(user):
    """ Only send student information to staff. """
    can_see_details = (current_user.is_authenticated
                        and (current_user.is_staff or user.id == current_user.id))
    if not can_see_details:
        return {}
    return user_json(user)

def ticket_json(ticket):
    return {
        'id': ticket.id,
        'status': ticket.status.name,
        'user': student_json(ticket.user),
        'created': ticket.created.isoformat(),
        'location': ticket.location,
        'assignment': ticket.assignment,
        'description': ticket.description,
        'question': ticket.question,
        'helper': ticket.helper and user_json(ticket.helper),
        'calendarEvent': ticket.calendar_event,
        'appointmentStartTime': ticket.appointment_start_time and \
            ticket.appointment_start_time.isoformat(),
    }

def emit_event(ticket, event_type):
    ticket_event = TicketEvent(
        event_type=event_type,
        ticket=ticket,
        user=current_user,
    )
    db.session.add(ticket_event)
    db.session.commit()
    socketio.emit('event', {
        'type': event_type.name,
        'ticket': ticket_json(ticket),
    })

def emit_presence(data):
    socketio.emit('presence', {k: len(v) for k,v in data.items()})

user_presence = collections.defaultdict(set) # An in memory map of presence.

@app.route('/')
@app.route('/<int:ticket_id>/')
def index(*args, **kwargs):
    return render_template('index.html')

def socket_error(message, category='danger', ticket_id=None):
    return {
        'messages': [
            {
                'category': category,
                'text': message,
            },
        ],
        'redirect': url_for('index', ticket_id=ticket_id),
    }

def socket_redirect(ticket_id=None):
    return {
        'redirect': url_for('index', ticket_id=ticket_id),
    }

def socket_unauthorized():
    return socket_error("You don't have permission to do that")

def logged_in(f):
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        if not current_user.is_authenticated:
            return socket_unauthorized()
        return f(*args, **kwds)
    return wrapper

def is_staff(f):
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        if not (current_user.is_authenticated and current_user.is_staff):
            return socket_unauthorized()
        return f(*args, **kwds)
    return wrapper

@socketio.on('connect')
def connect():
    if not current_user.is_authenticated:
        pass
    elif current_user.is_staff:
        user_presence['staff'].add(current_user.email)
    else:
        user_presence['students'].add(current_user.email)

    tickets = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.pending,
                           TicketStatus.assigned,
                           TicketStatus.appointment])
    ).all()
    emit('state', {
        'tickets': [ticket_json(ticket) for ticket in tickets],
        'appointments': appointments(),
        'currentUser':
            user_json(current_user) if current_user.is_authenticated else None,
    })
    emit_presence(user_presence)

@socketio.on('disconnect')
def disconnect():
    if not current_user.is_authenticated:
        pass
    elif current_user.is_staff:
        if current_user.email in user_presence['staff']:
            user_presence['staff'].remove(current_user.email)
    else:
        if current_user.email in user_presence['students']:
            user_presence['students'].remove(current_user.email)
    emit_presence(user_presence)

@socketio.on('refresh')
def refresh(ticket_ids):
    tickets = Ticket.query.filter(Ticket.id.in_(ticket_ids)).all()
    return {
        'tickets': [ticket_json(ticket) for ticket in tickets],
        'appointments': appointments()
    }

@socketio.on('create')
@logged_in
def create(form):
    """Stores a new ticket to the persistent database, and emits it to all
    connected clients.
    """
    my_ticket = Ticket.for_user(current_user)
    if my_ticket:
        return socket_error(
            'You are already on the queue',
            category='warning',
            ticket_id=my_ticket.ticket_id,
        )
    # Create a new ticket and add it to persistent storage
    if not (form.get('assignment') and form.get('question')
            and form.get('location')):
        return socket_error(
            'You must fill out all the fields',
            category='warning',
        )
    ticket = Ticket(
        status=TicketStatus.pending,
        user=current_user,
        assignment=form.get('assignment'),
        question=form.get('question'),
        location=form.get('location'),
    )

    db.session.add(ticket)
    db.session.commit()

    emit_event(ticket, TicketEventType.create)
    return socket_redirect(ticket_id=ticket.id)

def get_tickets(ticket_ids):
    return Ticket.query.filter(Ticket.id.in_(ticket_ids)).all()

def get_next_ticket():
    """Return the user's first assigned but unresolved ticket.
    If none exist, return to the first unassigned ticket.
    """
    ticket = Ticket.query.filter(
        Ticket.helper_id == current_user.id,
        Ticket.status == TicketStatus.assigned).first()
    if not ticket:
        ticket = Ticket.query.filter(
            Ticket.status == TicketStatus.pending).first()
    if ticket:
        return socket_redirect(ticket_id=ticket.id)
    else:
        return socket_redirect()

@socketio.on('next')
@is_staff
def next_ticket(ticket_ids):
    return get_next_ticket()

@socketio.on('delete')
@logged_in
def delete(ticket_ids):
    tickets = get_tickets(ticket_ids)
    for ticket in tickets:
        if not (current_user.is_staff or ticket.user.id == current_user.id):
            return socket_unauthorized()
        if ticket.status == TicketStatus.appointment:
            reopen_appointment(ticket.calendar_event)
        ticket.status = TicketStatus.deleted
        emit_event(ticket, TicketEventType.delete)
    db.session.commit()

@socketio.on('resolve')
@logged_in
def resolve(ticket_ids):
    tickets = get_tickets(ticket_ids)
    for ticket in tickets:
        if not (current_user.is_staff or ticket.user.id == current_user.id):
            return socket_unauthorized()
        ticket.status = TicketStatus.resolved
        emit_event(ticket, TicketEventType.resolve)
    db.session.commit()
    return get_next_ticket()

@socketio.on('assign')
@is_staff
def assign(ticket_ids):
    tickets = get_tickets(ticket_ids)
    for ticket in tickets:
        ticket.status = TicketStatus.assigned
        ticket.helper_id = current_user.id
        emit_event(ticket, TicketEventType.assign)
    db.session.commit()

@socketio.on('unassign')
@is_staff
def unassign(ticket_ids):
    tickets = get_tickets(ticket_ids)
    for ticket in tickets:
        ticket.status = TicketStatus.pending
        ticket.helper_id = None
        emit_event(ticket, TicketEventType.unassign)
    db.session.commit()

@socketio.on('load_ticket')
@is_staff
def load_ticket(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        return ticket_json(ticket)

@socketio.on('describe')
def describe(description):
    ticket_id, description = description['id'], description['description']
    ticket = Ticket.query.filter(Ticket.id == ticket_id).first()
    ticket.description = description
    emit_event(ticket, TicketEventType.describe)

    db.session.commit()

"""@socketio.on('make_appointment_slot')
@is_staff # TODO: This should not be accessible to lab assistants.
def make_appointment_slot():
    ""Creates a new appointment slot with the specified properties.
    ""
    pass"""

@socketio.on('appointments')
def appointments():
    """Returns a JSON blob of all available appointments.
    """
    response = calendar.service.events().list(
        calendarId=app.config.get('GOOGLE_CALENDAR_ID'),
        orderBy='startTime',
        timeMin=datetime.datetime.now().isoformat('T') + 'Z',
        singleEvents=True,
    ).execute()
    events = []
    for event in response['items']:
        if event['summary'] == '#appointment':
            events.append(calendar.event_json(event))
    return events
    
def reopen_appointment(calendar_event_id):
    event = calendar.service.events().get(
        calendarId=app.config.get('GOOGLE_CALENDAR_ID'),
        eventId=calendar_event_id).execute()
    if not event:
        return
    # Remove the student, notifying them via email
    event['attendees'] = []
    calendar.service.events().patch(
        calendarId=app.config.get('GOOGLE_CALENDAR_ID'),
        eventId=calendar_event_id,
        body=event,
        sendNotifications=True).execute()
    # Reset the event to be claimable by others
    event['summary'] = '#appointment'
    event['visibility'] = 'public'
    calendar.service.events().patch(
        calendarId=app.config.get('GOOGLE_CALENDAR_ID'),
        eventId=calendar_event_id,
        body=event,
        sendNotifications=False).execute()

@socketio.on('claim_appointment')
@app.route('/claim/<calendar_event_id>/')
@logged_in
def claim_appointment(calendar_event_id):
    """Claims an appointment for the current student and makes a ticket for it.
    """
    # Check that the event exists and is unclaimed
    event = calendar.service.events().get(
        calendarId=app.config.get('GOOGLE_CALENDAR_ID'),
        eventId=calendar_event_id).execute()
    if not event:
        return socket_error('Appointment does not exist', category='warning')
    
    if event['summary'] != '#appointment':
        return socket_error('Appointment has already been claimed',
                            category='warning')
    
    cost = calendar.find_cost(event['description'])
    
    if current_user.credit_balance < cost:
        return socket_error('Insufficient credit balance', category='warning')
    
    event['summary'] = app.config.get('COURSE_NAME') + ' Appointment'
    if ('attendees' not in event):
        event['attendees'] = []
    event['attendees'].append({
        'displayName': current_user.name,
        'email': current_user.email,
    })
    event['visibility'] = 'private'
    calendar.service.events().patch(
        calendarId=app.config.get('GOOGLE_CALENDAR_ID'),
        eventId=calendar_event_id,
        body=event,
        sendNotifications=True).execute()
    
    current_user.credit_balance -= cost
    
    start_time = dateutil.parser.parse(event['start']['dateTime'])
    start_time -= start_time.utcoffset()
    ticket = Ticket(
        status=TicketStatus.appointment,
        user=current_user,
        assignment="Appointment",
        question="Appointment",
        location=event['location'],
        calendar_event = calendar_event_id,
        appointment_start_time=start_time
    )

    db.session.add(ticket)
    db.session.commit()

    emit_event(ticket, TicketEventType.create)
    return socket_redirect(ticket_id=ticket.id)
    
