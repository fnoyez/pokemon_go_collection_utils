import datetime
import textwrap

from pokemon_go_collection.sources import bulbapedia as bulbapedia_m

# Two rows of the list as the page writes them, the first lending its label to
# the second, with a commented-out code, a note under an event, an event dated
# in its text and one whose date range crosses a year.
EVENT_POKEMON_TEXT = textwrap.dedent(
    """
    '''Event Pokémon''' are special forms.
    ==List of Event Pokémon==
    {| style="margin:auto;"
    |- style="background: #fff;"
    ! Form
    ! Pokémon
    ! Evolution only
    ! Availability
    |- style="background: #fff"
    | rowspan="2" | [[Cap Pikachu|Festive hat]]
    |{{MSP/GO|size=80|0172Holiday2016|Pichu}}{{MSP/GO|shadow=yes|size=80|0025Holiday2016|Pikachu}}
    |{{MSP/GO|size=80|0026Holiday2016|Raichu}}
    |
    * Holiday 2017: December 21, 2017 - January 4, 2018
    ** Festive {{GO|Pichu}} debut
    * Winter Holiday: December 28 - January 3, 2024 {{Shinystar/GO|Shiny possible}}
    ** Pichu only
    |- style="background: #fff"
    |{{MSP/GO|size=80|0025<!--0025Anniversary2026Thailand01-->|Pikachu}}
    |
    |
    * Since February 28, 2020, it has served as a reward {{Shinystar/GO|Shiny possible}}
    * PokéXciting! — Bangkok: ''To be announced''
    |}
    ==Trivia==
    """
)


def test_parse_event_pokemon():
    rows = bulbapedia_m.parse_event_pokemon(EVENT_POKEMON_TEXT)

    assert rows == [
        bulbapedia_m.EventPokemonRow(
            label="Festive hat",
            caught_sprites=(
                bulbapedia_m.Sprite(172, "Holiday2016", "Pichu"),
                bulbapedia_m.Sprite(25, "Holiday2016", "Pikachu"),
            ),
            evolution_only_sprites=(bulbapedia_m.Sprite(26, "Holiday2016", "Raichu"),),
            events=(
                bulbapedia_m.Event(
                    title="Holiday 2017",
                    start_date=datetime.date(2017, 12, 21),
                    is_shiny_possible=False,
                    notes=("Festive Pichu debut",),
                ),
                bulbapedia_m.Event(
                    title="Winter Holiday",
                    start_date=datetime.date(2023, 12, 28),
                    is_shiny_possible=True,
                    notes=("Pichu only",),
                ),
            ),
        ),
        bulbapedia_m.EventPokemonRow(
            label="Festive hat",
            caught_sprites=(
                bulbapedia_m.Sprite(25, "Anniversary2026Thailand01", "Pikachu"),
            ),
            evolution_only_sprites=(),
            events=(
                bulbapedia_m.Event(
                    title="Since February 28, 2020, it has served as a reward",
                    start_date=datetime.date(2020, 2, 28),
                    is_shiny_possible=True,
                    notes=(),
                ),
                bulbapedia_m.Event(
                    title="PokéXciting! — Bangkok",
                    start_date=None,
                    is_shiny_possible=False,
                    notes=(),
                ),
            ),
        ),
    ]
