Change Log
==========

Versioned according to [Semantic Versioning](http://semver.org/).

## Unreleased

## [2.0.3] - 2025-10-30

Fixed:

  * `ocrd-tool.json`: make tools conform to schema, #32

## [2.0.2] - 2025-05-21

Fixed:

  * ocrd-altotopdf: add missing resource file `PageConverter.jar`
  * multipage: resolve path names relative to workspace directory

Changed:

  * ocrd-altotopdf: allow running with missing ALTO files for some pages

## [2.0.1] - 2025-04-11

Fixed:

  * missing import, #29
  * more robust `mets:structMap` handling, #30
  * Dockerfile: `apt update` before `apt install`, #30

## [2.0.0] - 2025-03-12

Whats changed:

  * Fix typo in README.md by @konstantinschulz in #25
  * Remove unused batch files by @stweil in #26
  * Fix dockerimage creation by @joschrew in #27
  * rewrite: Pythonic, ocrd v3, utilise page-level annotation by @bertsky in #28
    * use Python instead of bashlib: faster, more flexible
    * include a distribution of the PRImA PDF converter as package data
    * instead of just the original image files, extract image data from the PAGE annotation, including any AlternativeImage
    * for that, introduce params image_feature_selector and image_feature_filter (e.g. cropped,deskewed,binarized)
    * support processing with METS Server and all new ocrd>=3.0 user-configurable features (page-parallel processing, page timeouts, error handling)
    * extend negative2zero to full PAGE validation and repairs for coordinates
    * back the font parameter by downloadable resources (ocrd resmgr); provide a variety of preconfigured fonts
    * multipage: add setting pagelabels=pagelabels for @ORDER and @ORDERLABEL from physical structMap
    * multipage: add parameter multipage_only to only keep the document-wide PDF, not the page-wise PDF files
    * multipage: add logical structMap divs as outline labels (PDF bookmarks)
    * multipage: improve and add more metadata, use proper formatting (string encoding, dates)
    * multipage: add MODS as extra XMP metadata payload
    * improve logging and relaying error messages
    * add processor ocrd-altotopdf (with limited features) besides ocrd-pagetopdf
    * add regression tests, CI and CD

## [1.1.0] - 2023-10-22

Whats changed:

  * various fixes by @bertsky in https://github.com/UB-Mannheim/ocrd_pagetopdf/pull/19
  * fix input-files, speed up I/O by @bertsky in https://github.com/UB-Mannheim/ocrd_pagetopdf/pull/22
  * Support for --mets-server-url by @kba in https://github.com/UB-Mannheim/ocrd_pagetopdf/pull/23
  * Use first bash from PATH (allows running on macOS) by @stweil in https://github.com/UB-Mannheim/ocrd_pagetopdf/pull/24

## [1.0.0] - 2020-09-28

First official release

<!-- link-labels -->
[2.0.3]: ../../compare/v2.0.3...v2.0.2
[2.0.2]: ../../compare/v2.0.2...v2.0.1
[2.0.1]: ../../compare/v2.0.1...v2.0.0
[2.0.0]: ../../compare/v2.0.0...v1.1.0
[1.1.0]: ../../compare/v1.1.0...v1.0.0
[1.0.0]: ../../compare/HEAD...v1.0.0
