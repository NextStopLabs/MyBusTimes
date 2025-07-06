(function($) {
    $(document).ready(function() {
        console.log("create_tracking.js loaded");

        let tripTimeData = {};

        function updateTimetableChoices() {
            const routeId = $('#id_tracking_route').val();
            const timetableField = $('#id_timetable');

            if (!routeId) return;

            $.ajax({
                url: '/api/get_timetables/',
                data: { route_id: routeId },
                success: function(data) {
                    timetableField.empty().append($('<option>').val('').text('---------'));
                    for (const [value, text] of Object.entries(data.timetables)) {
                        timetableField.append($('<option>').val(value).text(text));
                    }
                }
            });
        }

        function updateTimeChoices() {
            const timetableId = $('#id_timetable').val();
            const startTimeField = $('#id_start_time_choice');
            const startLocField = $('#id_tracking_start_location');
            const endLocField = $('#id_tracking_end_location');

            if (!timetableId) return;

            $.ajax({
                url: '/api/get_trip_times/',
                data: { timetable_id: timetableId },
                success: function(data) {
                    tripTimeData = data.times;

                    startTimeField.empty().append($('<option>').val('').text('---------'));
                    for (const [value, obj] of Object.entries(data.times)) {
                        startTimeField.append($('<option>').val(value).text(obj.label));
                    }

                    startLocField.val(data.start_stop);
                    endLocField.val(data.end_stop);
                }
            });
        }

        function pad(n) {
            return n < 10 ? '0' + n : n;
        }

        function todayStringWith(time) {
            const today = new Date();
            const [hour, minute] = time.split(':');
            return `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}T${hour}:${minute}`;
        }

        $('#id_tracking_route').change(function() {
            updateTimetableChoices();
            $('#id_start_time_choice').empty().append($('<option>').val('').text('---------'));
            $('#id_tracking_start_location').val('');
            $('#id_tracking_end_location').val('');
            $('#id_tracking_start_at').val('');
            $('#id_tracking_end_at').val('');
        });

        $('#id_timetable').change(function() {
            updateTimeChoices();
            $('#id_tracking_start_at').val('');
            $('#id_tracking_end_at').val('');
        });

        $('#id_start_time_choice').change(function() {
            const selectedTime = $(this).val();
            if (!selectedTime || !tripTimeData[selectedTime]) return;

            const startTime = tripTimeData[selectedTime].start_time;
            const endTime = tripTimeData[selectedTime].end_time;

            $('#id_tracking_start_at').val(todayStringWith(startTime));
            $('#id_tracking_end_at').val(todayStringWith(endTime));
        });
    });
})(jQuery);
