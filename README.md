# Buildkite Test Collector for Python (Beta)

The official Python adapter for [Buildkite Test Analytics](https://buildkite.com/test-analytics) which collects information about your tests.

**Supported python versions:** >=3.8

⚒ **Supported test frameworks:** pytest.

📦 **Supported CI systems:** Buildkite, GitHub Actions, CircleCI, and others via the `BUILDKITE_ANALYTICS_*` environment variables.


## 👉 Installing

1. [Create a test suite](https://buildkite.com/docs/test-analytics), and copy the API token that it gives you.

2. Add `buildkite-test-collector` to your list of dev dependencies in `setup.py`

```python
        extras_require={
            "dev": [
                "buildkite-test-collector"
            ]
        }
```

3. Set up your API token

Add the `BUIDLKITE_ANALYTICS_TOKEN` environment variable to your build system's environment.

4. Run your tests

Run your tests like normal.  Note that we attempt to detect the presence of several common CI environments, however if this fails you can set the `CI` environment variable to any value and it will work.

```sh
$ pytest
```

5. Verify that it works

If all is well, you should see the test run in the test analytics section of the Buildkite dashboard.

## 🎢 Tracing

The Buildkite Test Analytics REST API has support for tracing potentially slow operations within your tests, and can collect span data of [four types](https://buildkite.com/docs/test-analytics/importing-json#json-test-results-data-reference-span-objects): http, sql, sleep and annotations. This is documented as part of our public JSON API so anyone can instrument any code to send this data.

This library supports the ability to transmit tracing information to your Test Analytics output by using the new `spans` pytest fixture.  See [the `SpanCollector` documentation](https://github.com/buildkite/test-collector-python/blob/main/src/buildkite_test_collector/pytest_plugin/span_collector.py) for more information.

You may also need to manually capture the data you wish to trace for your use case. For examples of how we've done this in our Ruby test collector, see:
- [Instrumenting Rails to capture sql data](https://github.com/buildkite/test-collector-ruby/blob/9ac2b465cad647790d89b501a1754b06e47d5997/lib/buildkite/test_collector.rb#L107)
- [Monkey patching to various libraries to capture http requests](https://github.com/buildkite/test-collector-ruby/blob/9ac2b465cad647790d89b501a1754b06e47d5997/lib/buildkite/test_collector/network.rb#L58)
- [Monkey patching for sleep](https://github.com/buildkite/test-collector-ruby/blob/9ac2b465cad647790d89b501a1754b06e47d5997/lib/buildkite/test_collector/object.rb#L20)

Note: the Ruby test collector is the only Test Analytics collector that automatically captures and transmits span data. This Python collector can transmit information, but data capture must be done manually at this time.

## 🔜 Roadmap

See the [GitHub 'enhancement' issues](https://github.com/buildkite/test-collector-python/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) for planned features. Pull requests are always welcome, and we’ll give you feedback and guidance if you choose to contribute 💚

## ⚒ Developing

After cloning the repository, setup virtual environment (please skip this step if you are using `direnv`):

```bash
python -m venv .venv && source .venv/bin/activate
```

then install the dependencies:

```bash
pip install -e '.[dev]'
```

And run the tests:

```bash
pytest
```

Useful resources for developing collectors include the [Buildkite Test Analytics docs](https://buildkite.com/docs/test-analytics) and the [RSpec and Minitest collectors](https://github.com/buildkite/rspec-buildkite-analytics).

## 👩‍💻 Contributing

Bug reports and pull requests are welcome on GitHub at https://github.com/buildkite/test-collector-python

## 🚀 Releasing

1. Open a new PR bumping the version number in `constants.py`, make sure the PR title contains `[release]`.
2. Get the PR approved and merged, this will trigger the release pipeline.
3. (Optional) In the event of step 3 failure, run `.buildkite/steps/release-pypi` locally with your own credentials.
4. Create a [new github release](https://github.com/buildkite/test-collector-python/releases) for prosperity, you can create a tag as you create the release.

## 📜 License

The package is available as open source under the terms of the [MIT License](https://opensource.org/licenses/MIT).

## 🤙 Thanks

Thanks to the folks at [Alembic](https://alembic.com.au/) for building and maintaining this package.
