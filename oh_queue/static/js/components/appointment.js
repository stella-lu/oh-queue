let AppointmentSlot = ({state, appointment}) => {
  var startTime = moment.utc(appointment.startTime);
  var endTime = moment.utc(appointment.endTime);
  var dateDisplay = startTime.local().format('ddd M/D');
  var timeDisplay = startTime.local().format('h:mm A');
  var durationMinutes = endTime.diff(startTime) / 60000;
  
  function claim() {
    if (!confirm("Schedule an appointment for " + dateDisplay + " at " +
                 timeDisplay + " in " + appointment.location + ' for ' +
                 appointment.cost + ' credits?')) return;
    app.makeRequest('claim_appointment',appointment.eventId, true);
  }

  return (
    <div className="ticket-row clearfix" >
      <h5 className="pull-left">
        &nbsp;&nbsp;<small>{dateDisplay}</small>&nbsp;&nbsp;
        {timeDisplay} in {appointment.location}&nbsp;&nbsp;
        <small>{durationMinutes} minutes long</small>
      </h5>
      { state.currentUser && 
      <span className="pull-right">
        <button onClick={claim}
            className="btn btn-primary btn-small">
          Claim ({appointment.cost} credits)
        </button>&nbsp;
      </span>
      }
    </div>
  );
}
