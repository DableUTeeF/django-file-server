var dataTable = document.getElementById('data-table');
var checkItAll = dataTable.querySelector('input[name="read-all"]');
var inputs = dataTable.querySelectorAll('tbody>tr>td>input');

checkItAll.addEventListener('change', function() {
    if (checkItAll.checked) {
        inputs.forEach(function(input) {
            input.checked = true;
        });  
    }
});
$("a[rel~='keep-params']").click(function(e) {
    e.preventDefault();

    var params = window.location.search,
        dest = $(this).attr('href') + params;

    // in my experience, a short timeout has helped overcome browser bugs
    window.setTimeout(function() {
        window.location.href = dest;
    }, 100);
});
$(document).ready(
    $("form#table-form").submit(function(e) {
        e.preventDefault();
        var formData = new FormData(this);
        $.ajax({
            type:"POST",
            url: window.location.href,
            data:  formData,
            success: function(data){
                window.alert("success");
            },
            processData: false,
            contentType: false,
        });
    })
);
