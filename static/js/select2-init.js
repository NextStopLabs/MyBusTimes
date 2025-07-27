document.addEventListener('DOMContentLoaded', function() {
    const selects = document.querySelectorAll('.select2');
    selects.forEach(function(select) {
        $(select).select2();
    });
});
