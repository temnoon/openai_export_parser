# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-06

### Added
- Full production-ready implementation of OpenAI export parser
- Comprehensive test suite (34 tests, 73% coverage)
- GitHub Actions CI/CD workflows
- Issue and PR templates
- Complete documentation (README, CONTRIBUTING)
- MIT License

### Features
- Recursive zip extraction with nested archive support
- **Robust zip handling** - Fallback extraction for malformed archives
  - Tries Python's `zipfile` first (fast)
  - Falls back to macOS `ditto` on macOS (same as Archive Utility)
  - Falls back to system `unzip` with lenient error handling
  - Accepts partial extractions if files were recovered
- Automatic schema inference for future-proof parsing
- Intelligent media matching (filenames, file-IDs, UUIDs)
- Conversation threading with parent/child relationships
- Progress tracking with tqdm
- Verbose logging mode
- CLI with argparse

### Fixed
- **[CRITICAL]** Handle malformed OpenAI export zips that cause "Bad magic number" errors
  - Successfully parses exports with structural issues (4GB+ offset errors)
  - Works with exports that macOS Archive Utility can open but Python zipfile cannot
- Media file deduplication (same basename handling)

### Tested
- Verified with real OpenAI export containing:
  - 3,646 conversations
  - 10,488 media files (4,433 unique)
  - 29 nested DALL-E image archives
  - 6 nested file archives
  - Complex mapping structures with full metadata

## [0.1.0] - 2025-01-06

### Added
- Initial project structure
- Basic skeleton implementation

---

## Release Notes

### v0.2.0 - Production Ready

This release marks the first production-ready version of the OpenAI Export Parser.

**Major Highlights:**

1. **Robust Zip Handling** - The parser can now handle malformed zip files that Python's standard library cannot process. This was tested with a real OpenAI export that had "4294967296 extra bytes at beginning" errors. The parser successfully extracted all data using fallback methods.

2. **Real-World Tested** - Successfully parsed a production export containing 3,646 conversations and 10,488 media files, including 29 nested DALL-E archives.

3. **Complete Test Suite** - 34 comprehensive tests covering all core functionality with 73% code coverage.

4. **GitHub Ready** - Full CI/CD setup with automated testing across multiple Python versions and operating systems.

**Breaking Changes:** None (initial release)

**Migration Guide:** N/A (initial release)

**Known Issues:**
- Media deduplication may reduce media count if multiple files share the same basename
- CLI coverage at 0% (CLI functionality tested manually)
- Some utils.py error handling paths not covered by unit tests (covered by integration testing)

**Next Steps:**
- Consider adding conversation search/filter capabilities
- Add export format migration tools
- Create visualization tools for conversation threads
- Implement incremental parsing for very large exports
