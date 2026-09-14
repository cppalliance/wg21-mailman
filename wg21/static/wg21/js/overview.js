(function ($) {
    "use strict";

    var TALL_BAR_CUTOFF = 35;

    function root() {
        return $(".wg21-overview");
    }

    function markTallBars($scope) {
        $scope.find(".chart-data .bars rect").each(function () {
            this.classList.toggle(
                "is-tall",
                parseFloat(this.getAttribute("height")) > TALL_BAR_CUTOFF
            );
        });
    }

    function refresh() {
        var $root = root();
        if (!$root.length) {
            return;
        }
        markTallBars($root);
    }

    window.wg21Overview = {
        init: function (activityUrl) {
            setup_overview(activityUrl);
            refresh();
            $(document).ajaxComplete(function () {
                refresh();
            });
        }
    };
}(jQuery));
