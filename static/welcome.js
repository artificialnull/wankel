$('#login_reveal').click(function() {
    $('#input_div').show('fast', function() {});
    $('#login_reveal').removeClass('white-text').addClass('red-text');
    $('#signup_reveal').removeClass('red-text').addClass('white-text');
});

$('#signup_reveal').click(function() {
    $('#input_div').show('fast', function() {});
    $('#signup_reveal').removeClass('white-text').addClass('red-text');
    $('#login_reveal').removeClass('red-text').addClass('white-text');
});

$('#submit').click(function () {
    params={};location.search.replace(/[?&]+([^=&]+)=([^&]*)/gi,function(s,k,v){params[k]=v});
    console.log(params.next)
    $.ajax({
        type: "POST",
        contentType: "application/json; charset=utf-8",
        url: ($('#login_reveal').hasClass('red-text') ? "/login" : '/signup'),
        data: JSON.stringify({name: $('#username').val(), pass: $('#password').val()}),
        success: function (data) {
            console.log(data);
            window.location.href = "http://kamat.xyz:5000" + (params.next == undefined ? '' : unescape(params.next));
        },
        dataType: "json"
    });
});
