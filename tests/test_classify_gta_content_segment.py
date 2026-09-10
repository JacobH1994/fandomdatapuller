"""Tests for etl/classify_gta_content_segment.py's tag/title matching --
encodes the real false-positive and true-positive tags found by pulling
every distinct GTA V tag seen in platform_viewership_snapshots (2026-09-10),
before the classifier was written, not invented cases."""

from etl.classify_gta_content_segment import classify_row, classify_tag


# Real tags observed that must NOT match (contain "rp" mid-word, no
# roleplay connection) -- a naive substring-anywhere check on "rp" fails
# every one of these.
def test_career_progress_tag_is_not_rp():
    assert classify_tag("CareerProgress") is None


def test_burps_and_farts_tag_is_not_rp():
    assert classify_tag("BurpsAndFarts") is None


def test_sharpness_tag_is_not_rp():
    assert classify_tag("Sharpness") is None


def test_content_creator_program_tag_is_not_rp():
    assert classify_tag("ContentCreatorProgram") is None


def test_controllerplayer_tag_is_not_rp():
    assert classify_tag("controllerplayer") is None


def test_partner_push_tags_are_not_rp():
    assert classify_tag("PartnerPush") is None
    assert classify_tag("TwitchPartnerPush") is None
    assert classify_tag("PushForPartner") is None


def test_rpg_genre_tags_are_not_gta_rp():
    # RPG (role-playing GAME genre) is a different concept from GTA
    # roleplay servers -- deliberately not matched.
    assert classify_tag("RPG") is None
    assert classify_tag("MMORPG") is None
    assert classify_tag("TTRPGs") is None
    assert classify_tag("JRPGLover") is None


# Real compound tags observed that MUST match -- smashed-together, no
# internal word boundary, which is why word-boundary regex (the
# classify_broadcast_tier.py convention) would silently miss them.
def test_compound_rp_suffix_tags_match():
    assert classify_tag("LegacyRP") == "gta_rp_other"
    assert classify_tag("MajesticRP") == "gta_rp_other"
    assert classify_tag("CapitalRP") == "gta_rp_other"
    assert classify_tag("GtaRp") == "gta_rp_other"


def test_bare_rp_tag_matches():
    assert classify_tag("RP") == "gta_rp_other"
    assert classify_tag("rp") == "gta_rp_other"


def test_roleplay_fivem_gtarp_substrings_match_anywhere():
    assert classify_tag("Roleplay") == "gta_rp_other"
    assert classify_tag("GTAVFiveM") == "gta_rp_other"
    assert classify_tag("DanskFiveM") == "gta_rp_other"
    assert classify_tag("GTARP") == "gta_rp_other"


def test_tarp_family_prefix_matches():
    assert classify_tag("TarpAmbassador") == "gta_rp_other"
    assert classify_tag("TARPPartnered") == "gta_rp_other"
    assert classify_tag("TARPAmbassadorServer") == "gta_rp_other"


def test_larp_matches_via_suffix():
    assert classify_tag("LARP") == "gta_rp_other"
    assert classify_tag("ThePalmsLARp") == "gta_rp_other"


# NoPixel-specific -- most specific tier, checked ahead of the broader
# RP bucket.
def test_nopixel_tag_variants_match_nopixel_not_gta_rp_other():
    for tag in ["NoPixel", "NOPIXELV", "nopixelrp", "NopixelWL", "gtanopixel"]:
        assert classify_tag(tag) == "nopixel"


# Full-row classification -- title text uses word-boundary matching
# (prose), tags use the substring/suffix/prefix rules above. NoPixel
# wins over the broader bucket if both would match.
def test_row_classified_nopixel_from_title_even_without_tag():
    assert classify_row("Chatterbox | NoPixel V | DAY 2", "English,DropsEnabled") == "nopixel"


def test_row_classified_nopixel_from_tag_even_with_generic_title():
    assert classify_row("just vibing", "English,NoPixel,DropsEnabled") == "nopixel"


def test_row_classified_gta_rp_other_from_compound_tag():
    assert classify_row("Some RP session", "English,LegacyRP,Dansk") == "gta_rp_other"


def test_row_classified_non_rp_when_nothing_matches():
    assert classify_row("Stunt jumps and chaos in Los Santos", "English,Stunts,Funny") == "non_rp"


def test_row_title_cyberpunk_false_positive_does_not_trigger_rp():
    # "Cyberpunk2077" contains "rp" mid-word in free text too -- word
    # boundary matching on the title must reject it the same way the tag
    # suffix rule does.
    assert classify_row("Playing Cyberpunk2077 tonight", "English") == "non_rp"


def test_row_title_word_boundary_rp_still_matches_as_standalone_word():
    assert classify_row("GTA RP with the boys", "English") == "gta_rp_other"


def test_nopixel_precedence_over_broader_rp_bucket_on_same_row():
    assert classify_row("NoPixel V session", "English,Roleplay,NoPixel") == "nopixel"
