let Ticket = ({state, ticket}) => {
  var status;
  if (ticket.status === 'pending') {
    status = ticketDisplayTime(ticket) + ' in ' + ticket.location;
  } else {
    if (isStaff(state)) {
      status = (isTicketHelper(state, ticket) ? 'you' : ticket.helper.name) + ' (' + ticketTimeAgo(ticket)+ ')';
    } else {
      status = ticketStatus(state, ticket);
    }
  }

  var description;
  if (isStaff(state) || ticketIsMine(state, ticket)) {
    description = ticket.description;
  }
  
  var dateDisplay, timeDisplay;
  if (ticket.status === 'appointment') {
    var startTime = moment.utc(ticket.appointmentStartTime);
    dateDisplay = startTime.local().format('ddd M/D');
    timeDisplay = startTime.local().format('h:mm A');
  }
  
  if (ticket.status === 'appointment') {
    return (
      <TicketLink state={state} ticket={ticket}>
        <h4 className="pull-left">&nbsp;&nbsp;
           {isStaff(state) && <span>Appointment with {ticket.user.name} at {timeDisplay} on {dateDisplay} in {ticket.location}</span>}
           {!isStaff(state) && <span>Appointment at {timeDisplay} on {dateDisplay} in {ticket.location}</span>}
          <br className="visible-xs" />
          <small className="visible-xs ticket-desc-xs">{description}</small>
        </h4>
        <h4 className="pull-left hidden-xs ticket-desc-md "><small>{description}</small></h4>
      </TicketLink>
    )
  }

  return (
    <TicketLink state={state} ticket={ticket}>
      <div className="pull-left ticket-index">{ticketPosition(state, ticket)}</div>
      <h4 className="pull-left">
        {ticket.assignment} Q{ticket.question}
        <br className="visible-xs" />
        <small className="visible-xs ticket-status-xs">{status}</small>
        <small className="visible-xs ticket-desc-xs">{description}</small>
      </h4>
      <h4 className="pull-left hidden-xs ticket-desc-md "><small>{description}</small></h4>

      <h4 className="pull-right hidden-xs ticket-status-md"><small>{status}</small></h4>

    </TicketLink>
  );
}

let TicketLink = ({state, ticket, children}) => {
  let highlight = ticketIsMine(state, ticket) || isTicketHelper(state, ticket);
  let link = ticketIsMine(state, ticket) || isStaff(state);
  let ticketClass = classNames({
    'ticket-row': true,
    'clearfix': true,
    'ticket-link': link,
    'ticket-highlight': highlight,
  });
  if (link) {
    return (
      <div className={ticketClass}>
        <ReactRouter.Link to={`/${ticket.id}/`} className="clearfix">
          {children}
        </ReactRouter.Link>
      </div>
    );
  } else {
    return (
      <div className={ticketClass}>
        {children}
      </div>
    );
  }
}
