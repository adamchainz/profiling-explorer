=========
Changelog
=========

Unreleased
----------

* Shorten standard library and installed package paths on Windows.

  `PR #70 <https://github.com/adamchainz/profiling-explorer/pull/>`__.

1.3.1 (2026-10-29)
------------------

* Fix crash on Windows when profiled files are on a different drive to the current directory.

  `PR #69 <https://github.com/adamchainz/profiling-explorer/pull/69>`__.
  Thanks to Serdar Yegulalp for the report in `Issue #40 <https://github.com/adamchainz/profiling-explorer/issues/40>`__.

1.3.0 (2026-10-29)
------------------

* Drop Python 3.10 support.

  `PR #58 <https://github.com/adamchainz/profiling-explorer/pull/58>`__.

* Support Python 3.15.

  `PR #52 <https://github.com/adamchainz/profiling-explorer/pull/52>`__.

* Add a **ms/call** column, showing cumulative time divided by number of calls.

  `PR #66 <https://github.com/adamchainz/profiling-explorer/pull/66>`__.

* Click a filename to open it at that line in your editor.
  profiling-explorer now uses `launch-editor-py <https://pypi.org/project/launch-editor-py/>`__ to find your editor and use it to open file locations on click.

  `PR #68 <https://github.com/adamchainz/profiling-explorer/pull/68>`__.

* Make the back link on callers and callees pages restore the main table’s search and sort order.

  `PR #67 <https://github.com/adamchainz/profiling-explorer/pull/67>`__.

* Fix the focal row being repeated on every page of long callers and callees lists.

  `PR #61 <https://github.com/adamchainz/profiling-explorer/pull/61>`__.

* Fix server error on invalid pagination offsets.

  `PR #62 <https://github.com/adamchainz/profiling-explorer/pull/62>`__.

* Fix rows from an older page load being appended after a search replaced the table.

  `PR #65 <https://github.com/adamchainz/profiling-explorer/pull/65>`__.

* Switch package build backend from setuptools to `uv_build <https://docs.astral.sh/uv/concepts/build-backend/>`__.
  This makes builds with uv about nine times faster, since uv runs the backend natively, without creating a build environment or spawning a Python process.
  Additionally, source distributions no longer include test files, which setuptools previously included incompletely, missing the files needed to actually run them.

  `PR #51 <https://github.com/adamchainz/profiling-explorer/pull/51>`__.

1.2.0 (2026-05-18)
------------------

* Enable changing the sort order in callees and callers views.

  `PR #43 <https://github.com/adamchainz/profiling-explorer/pull/43>`__.

1.1.2 (2026-04-14)
------------------

* Fix caller percentage calculation.

  `PR #37 <https://github.com/adamchainz/profiling-explorer/pull/37>`__.

1.1.1 (2026-04-13)
------------------

* Fix filename simplification.

  `PR #36 <https://github.com/adamchainz/profiling-explorer/pull/36>`__.

1.1.0 (2026-04-13)
------------------

* Extend search to support multiple terms.

  `PR #33 <https://github.com/adamchainz/profiling-explorer/pull/33>`__.

* Add keyboard shortcuts to focus the search box.

  `PR #35 <https://github.com/adamchainz/profiling-explorer/pull/35>`__.

* Fix callers/callees views for built-in functions.

  `PR #34 <https://github.com/adamchainz/profiling-explorer/pull/34>`__.
  Thanks to David Szotten for the report in `Issue #32 <https://github.com/adamchainz/profiling-explorer/issues/32>`__.

1.0.1 (2026-04-02)
------------------

* Fix crash when a record has an empty filename.

1.0.0 (2026-04-02)
------------------

* Initial release.
