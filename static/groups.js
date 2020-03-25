$('#create-group').click(function() {
    $('#new-group-div').show('fast', function() {});
    $('#create-group').hide('fast', function() {});
});

$('#submit').click(function () {
    $.ajax({
        type: "POST",
        contentType: "application/json; charset=utf-8",
        url: '/create-group',
        data: JSON.stringify({name: $('#name').val(), pass: $('#password').val(), description: $('#description').val()}),
        success: function (data) {
            console.log(data);
            if (data.success) {
                window.location.href = window.location.origin + '/';
            }
        },
        dataType: "json"
    });
});
