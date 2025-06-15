# Changelog

## future release
### Added
- ability to create and run pipelines (e.g. for recording to db, generate map plot and video files)
- add user authentication for upload and jobs pages on dashboard
- complete writing tests for CLI and utils (requires sample .mcap recording with NavSatFix and Image which can be shared)

### Changed
- integrate future streamlit updates regarding theming and dataframe which were announced in Q4 2024 Showcase

### Fixed


## v0.2.0 - 2025-06-15
### Added
- Expanded configuration options, including:
    - Enable/disable link for the path column on the dashboard
    - Timezone settings
    - Customizable dashboard name and logo path
- Support for reusing existing metadata or regenerating metadata files.
- Refactored database interface with added support for MongoDB and Elasticsearch, including authentication.
- New CLI commands:
    - `metadata` for managing metadata files.
    - `connection` for handling database connections.
    - `database_sort_by` for sorting database entries.

### Fixed
- Resolved numerous minor bugs to improve stability and performance.

## v0.1.0 - 2025-03-27
### Added
- initial dashboard
- initial CLI
- initial utils for mcap, db
- add pyproject.toml for bagman CLI
