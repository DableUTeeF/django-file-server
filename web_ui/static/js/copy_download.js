
function copy_download_hash(name, checked) {
    console.log(name);
    console.log(checked);
    $.ajaxSetup({ 
        beforeSend: function(xhr, settings) {
            function getCookie(name) {
                var cookieValue = null;
                if (document.cookie && document.cookie != '') {
                    var cookies = document.cookie.split(';');
                    for (var i = 0; i < cookies.length; i++) {
                        var cookie = jQuery.trim(cookies[i]);
                        // Does this cookie string begin with the name we want?
                        if (cookie.substring(0, name.length + 1) == (name + '=')) {
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }
                    }
                }
                return cookieValue;
            }
            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                // Only send the token to relative URLs i.e. locally.
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        } 
    });
    $.ajax({
        type:"POST",
        url: "/gethash/",
        data: {
            pathname: window.location.pathname,
            name: name,
            // csrfmiddlewaretoken: '{{ csrf_token }}'
        },
        success: function(data){

            document.getElementById(name).hidden = true;
            document.getElementById(checked).hidden = false;
            window.alert(data.hash);
            navigator.clipboard.writeText("Download link\n" + data.hash);
        },
        // processData: false,
        // contentType: false,
    });
}
