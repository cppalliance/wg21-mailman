(function ($) {
    "use strict";

    var TALL_BAR_CUTOFF = 35;

    function root() {
        return $(".wg21-overview");
    }

    function fillPosterInitials($scope) {
        $scope.find(".wg21-poster__avatar[data-name]").each(function () {
            var $el = $(this);
            var $initials = $el.find(".wg21-poster__initials");
            if (!$initials.length || $initials.text()) {
                return;
            }
            var parts = ($el.attr("data-name") || "").trim().split(/\s+/).filter(Boolean);
            var letters = "";
            if (parts.length >= 2) {
                letters = parts[0].charAt(0) + parts[parts.length - 1].charAt(0);
            } else if (parts.length === 1) {
                letters = parts[0].slice(0, 2);
            }
            $initials.text(letters.toUpperCase());
        });
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
        fillPosterInitials($root);
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
