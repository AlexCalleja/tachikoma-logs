from log_parser import calc_cost, get_tier


def test_get_tier_opus():
    assert get_tier("claude-opus-4-7") == "opus"


def test_get_tier_haiku():
    assert get_tier("claude-haiku-4-5") == "haiku"


def test_get_tier_sonnet():
    assert get_tier("claude-sonnet-4-6") == "sonnet"


def test_get_tier_default_for_unknown():
    assert get_tier("unknown-model") == "sonnet"


def test_get_tier_default_for_empty():
    assert get_tier("") == "sonnet"


def test_calc_cost_zero_usage():
    assert calc_cost({}, "sonnet") == 0.0


def test_calc_cost_output_tokens_sonnet():
    # sonnet output: $15 per 1M tokens
    assert calc_cost({"output_tokens": 1_000_000}, "sonnet") == 15.0


def test_calc_cost_input_tokens_opus():
    # opus input: $15 per 1M tokens
    assert calc_cost({"input_tokens": 1_000_000}, "opus") == 15.0


def test_calc_cost_cache_read_opus():
    # opus cache_read: $1.50 per 1M tokens
    assert calc_cost({"cache_read_input_tokens": 1_000_000}, "opus") == 1.50


def test_calc_cost_all_components_sonnet():
    # sonnet: input $3, output $15, cache_read $0.30, cache_create $3.75 per 1M
    usage = {
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "cache_read_input_tokens": 1_000_000,
        "cache_creation_input_tokens": 1_000_000,
    }
    assert calc_cost(usage, "sonnet") == 3.0 + 15.0 + 0.30 + 3.75
