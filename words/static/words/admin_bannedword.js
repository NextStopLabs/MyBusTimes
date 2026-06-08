(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const selectAll = document.getElementById('id_ban_all');
        const scopeBoxes = [
            'id_ban_search',
            'id_ban_operator_name',
            'id_ban_group_name',
            'id_ban_username',
        ].map(function (id) {
            return document.getElementById(id);
        }).filter(Boolean);

        if (!selectAll || scopeBoxes.length === 0) {
            return;
        }

        const updateSelectAll = function () {
            selectAll.checked = scopeBoxes.every(function (box) {
                return box.checked;
            });
        };

        selectAll.addEventListener('change', function () {
            scopeBoxes.forEach(function (box) {
                box.checked = selectAll.checked;
            });
        });

        scopeBoxes.forEach(function (box) {
            box.addEventListener('change', updateSelectAll);
        });

        updateSelectAll();
    });
})();
