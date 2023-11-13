# Changelog

## [v0.1.7](https://github.com/XaviArnaus/mastodon-echo-bot/releases/tag/v0.1.7)

### Added

- Support for Firefish instances. This is an initial step to bring together the Publishing features between this Echo bot and the [Janitor](https://github.com/XaviArnaus/janitor) projects.
- A new runner to test the current state of the Publishing to Mastodon API flow

### Changed

- The split content (basically done in the Telegram parser) is published as a thread and not as individual posts anymore

## [v0.1.6](https://github.com/XaviArnaus/mastodon-echo-bot/releases/tag/v0.1.6)

### Added

- A new runner to test the current state of the Janitor monitoring

## [v0.1.5](https://github.com/XaviArnaus/mastodon-echo-bot/releases/tag/v0.1.5)

### Changed

- Adding a simple deduplication strategy into the feed migration script to remove duplicates that appear when cleaning the URL.

## [v0.1.4](https://github.com/XaviArnaus/mastodon-echo-bot/releases/tag/v0.1.4)

### Changed

- Pinning `pyxavi` to `v0.6.0`, acquiring the new `Url` class and the deprecation of `logger.getLogger()`

## [v0.1.3](https://github.com/XaviArnaus/mastodon-echo-bot/releases/tag/v0.1.3)

### Added

- A script to update the current *feeds* storage file so that the URLs loose their scheme.

### Changed

- Removed the `scheme` on the URLs stored in the *feeds* file to avoid duplicates, to overcome issues with RSS providers that changes from HTTPS to HTTP randomly (Hello #ivoox)

## [v0.1.2](https://github.com/XaviArnaus/mastodon-echo-bot/releases/tag/v0.1.2)

### Changed

- Bugfix on the `Publisher` class introduced in the previous version `v0.1.1` that refused to publish any post.
- Pinning `pyxavi` to the current set up `v0.3.2` to avoid receiving the deprecation of `logger.getLogger()`

## [v0.1.1](https://github.com/XaviArnaus/mastodon-echo-bot/releases/tag/v0.1.1)

### Added

- Initial Mastodon Publisher retries logic to overcome issue `422, 'Unprocessable Content', 'Cannot attach files that have not finished processing. Try again in a moment!'`

## [v0.1.0](https://github.com/XaviArnaus/mastodon-echo-bot/releases/tag/v0.1.0)

### Added

- First version of `Changelog.md`. all changes until now get stashed ;-)