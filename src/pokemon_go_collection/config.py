import dataclasses
import datetime
import pathlib

DEFAULT_APP_HOME_FOLDER_PATH = pathlib.Path.home() / ".pokemon_go_collection"
DEFAULT_BACKUP_FOLDER_PATH = pathlib.Path(
    "/home/pavel/Data/Projects/data/.pokemon_go_collection_db_backup"
)
REPOSITORY_FOLDER_PATH = pathlib.Path(__file__).resolve().parents[2]


@dataclasses.dataclass(frozen=True)
class AppConfig:
    db_file_path: pathlib.Path
    backup_folder_path: pathlib.Path
    # The last successfully fetched copy of each downloaded source.
    sources_folder_path: pathlib.Path
    # Served by Streamlit, which serves files only from `static/` next to the
    # script it runs.
    icons_folder_path: pathlib.Path
    # The committed reference data: National Pokédex seed and overrides.
    data_folder_path: pathlib.Path
    game_master_repository_folder_path: pathlib.Path
    refresh_period_duration: datetime.timedelta


def load_config(
    app_home_folder_path,
    backup_folder_path,
    repository_folder_path,
    refresh_period_duration=datetime.timedelta(days=7),
):
    """Build the configuration, creating the application folders, and fail fast on an invalid path."""
    if not backup_folder_path.is_dir():
        raise FileNotFoundError(f"Backup folder does not exist: {backup_folder_path}")
    game_master_repository_folder_path = repository_folder_path.parent / "game_masters"
    if not (game_master_repository_folder_path / "latest" / "latest.json").is_file():
        raise FileNotFoundError(
            f"No game master found in {game_master_repository_folder_path}: "
            "clone PokeMiners/game_masters there"
        )

    sources_folder_path = app_home_folder_path / "sources"
    sources_folder_path.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        db_file_path=app_home_folder_path / "collection.sqlite",
        backup_folder_path=backup_folder_path,
        sources_folder_path=sources_folder_path,
        icons_folder_path=repository_folder_path / "static" / "icons",
        data_folder_path=repository_folder_path / "data",
        game_master_repository_folder_path=game_master_repository_folder_path,
        refresh_period_duration=refresh_period_duration,
    )
