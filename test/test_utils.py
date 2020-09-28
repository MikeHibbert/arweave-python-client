from arweave.utils import winston_to_ar, ar_to_winston


def test_winston_to_ar():
    fee = {
        "winston": "938884",
        "ar": "0.000000938884"
    }

    ar = winston_to_ar(fee['winston'])
    assert ar == float(fee["ar"])


def test_ar_to_winston():
    fee = {
        "winston": "938884",
        "ar": "0.000000938884"
    }

    winston = ar_to_winston(fee['ar'])

    assert winston == fee["winston"]


if __name__ == "__main__":
    test_ar_to_winston()
    test_winston_to_ar()
