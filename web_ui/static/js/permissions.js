var dataTable = document.getElementById('data-table');
var read_all = dataTable.querySelector('input[name="read-all"]');
var write_all = dataTable.querySelector('input[name="write-all"]');
var read_inputs = dataTable.querySelectorAll('tbody>tr>td>input[name^="read-"]');
read_inputs = Array.from(read_inputs);
read_inputs = read_inputs.splice(1, read_inputs.length) 
var write_inputs = dataTable.querySelectorAll('tbody>tr>td>input[name^="write-"]');
write_inputs = Array.from(write_inputs);
write_inputs = write_inputs.splice(1, write_inputs.length) 
read_all.addEventListener('change', function() {
    if (read_all.checked) {
        read_inputs.forEach(function(input) {
            input.checked = true;
        });  
    }
    else {
        read_inputs.forEach(function(input) {
            input.checked = false;
        });  
    }
});
write_all.addEventListener('change', function() {
    if (write_all.checked) {
        write_inputs.forEach(function(input) {
            input.checked = true;
        });  
    }
    else {
        write_inputs.forEach(function(input) {
            input.checked = false;
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
