$(document).ready(function(){
    $('.timepicker').timepicker({
        twelveHour: false,
    });
});

$('#submit').click(function () {
    $.ajax({
        type: "POST",
        contentType: "application/json; charset=utf-8",
        url: '/create-event',
        data: JSON.stringify({
            start: $('#start_time').val(),
            end: $('#end_time').val(),
            description: $('#description').val()
        }),
        success: function (data) {
            console.log(data);
            if (data.success) { location.reload(); }
        },
        dataType: "json"
    });
});
