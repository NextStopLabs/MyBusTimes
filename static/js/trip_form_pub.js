(function($) {
    $(document).ready(function() {
        console.log("trip_form.js loaded");  // Debug log
        
        function updateTimetableChoices() {
            console.log('Updating timetable choices');
            const routeId = $('#id_trip_route').val();
            console.log('Route ID:', routeId);
            const timetableField = $('#id_timetable');

            if (!routeId) {
                console.log('No route ID selected, returning');
                return;
            }

            console.log('Making AJAX request for timetables');
            $.ajax({
                url: '/api/get_timetables/',
                data: {
                    route_id: routeId
                },
                success: function(data) {
                    console.log('Timetable data received:', data);
                    timetableField.empty();
                    timetableField.append($('<option>').val('').text('---------'));
                    for (const [value, text] of Object.entries(data.timetables)) {
                        console.log('Adding timetable option:', value, text);
                        timetableField.append($('<option>').val(value).text(text));
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error fetching timetables:', status, error);
                }
            });
        }

        function updateTimeChoices() {
            console.log('Updating time choices');
            const timetableId = $('#id_timetable').val();
            console.log('Timetable ID:', timetableId);
            const startTimeField = $('#id_start_time_choice');

            if (!timetableId) {
                console.log('No timetable ID selected, returning');
                return;
            }

            console.log('Making AJAX request for trip times');
            $.ajax({
                url: '/api/get_trip_times/',
                data: {
                    timetable_id: timetableId
                },
                success: function(data) {
                    console.log('Trip times data received:', data);
                    startTimeField.empty();
                    startTimeField.append($('<option>').val('').text('---------'));
                    for (const [value, label] of Object.entries(data.times)) {
                        console.log('Adding time option:', value, label);
                        startTimeField.append($('<option>').val(value).text(label));
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error fetching trip times:', status, error);
                }
            });
        }

        console.log('Setting up event handlers');
        $('#id_trip_route').change(function() {
            console.log('Route changed');
            updateTimetableChoices();
            $('#id_start_time_choice').empty().append($('<option>').val('').text('---------'));
        });

        $('#id_timetable').change(function() {
            console.log('Timetable changed');
            updateTimeChoices();
        });
    });
})(jQuery);
