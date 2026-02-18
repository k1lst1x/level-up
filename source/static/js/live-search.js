(function () {
  function norm(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/[\s,]+/g, " ")
      .trim();
  }

  function stems(word) {
    var variants = [word];
    for (var i = 1; i <= 3; i++) {
      if (word.length - i >= 3) {
        variants.push(word.slice(0, -i));
      }
    }
    return variants;
  }

  function queryWords(query) {
    return norm(query)
      .split(" ")
      .filter(function (word) {
        return word.length >= 2;
      });
  }

  function matches(haystack, words) {
    return words.every(function (word) {
      return stems(word).some(function (stem) {
        return haystack.indexOf(stem) !== -1;
      });
    });
  }

  function initLiveSearch(root) {
    var input = root.querySelector("[data-live-search-input]");
    if (!input) return;

    var items = Array.prototype.slice.call(
      root.querySelectorAll("[data-live-search-item]")
    );
    if (!items.length) return;

    var empty = root.querySelector("[data-live-search-empty]");

    function applyFilter() {
      var words = queryWords(input.value);
      var visibleCount = 0;

      items.forEach(function (item) {
        var haystack = norm(item.getAttribute("data-search") || item.textContent);
        var show = words.length === 0 || matches(haystack, words);
        item.style.display = show ? "" : "none";
        if (show) visibleCount += 1;
      });

      if (empty) {
        empty.style.display = visibleCount === 0 && words.length > 0 ? "" : "none";
      }
    }

    input.addEventListener("input", applyFilter);
    applyFilter();
  }

  function boot() {
    var roots = document.querySelectorAll("[data-live-search-root]");
    roots.forEach(initLiveSearch);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
