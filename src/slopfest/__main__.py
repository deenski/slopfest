from importlib.metadata import PackageNotFoundError, version


def _assert_pygame_ce() -> None:
    try:
        version("pygame-ce")
    except PackageNotFoundError as exc:
        raise SystemExit(
            "Slopfest requires pygame-ce. Install with: python -m pip install pygame-ce"
        ) from exc

    # pygame-ce intentionally owns the `pygame` import namespace. Refuse to run
    # if upstream pygame is installed too, because the two packages collide.
    try:
        upstream = version("pygame")
    except PackageNotFoundError:
        upstream = None

    if upstream is not None:
        raise SystemExit(
            "The upstream 'pygame' distribution is installed alongside pygame-ce. "
            "Remove it with: python -m pip uninstall pygame"
        )


def main() -> None:
    _assert_pygame_ce()
    from .game import Game
    Game().run()


if __name__ == "__main__":
    main()
