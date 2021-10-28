START_BYTE = 2
END_BYTE = 3
CHAT_LOG_SPLITTER = b"\x1f"


class SeStringChunkType(object):
    ICON = 0x12
    EMPHASIS_ITALIC = 0x1A
    SE_HYPHEN = 0x1F
    INTERACTABLE = 0x27
    AUTO_TRANSLATE_KEY = 0x2E
    UI_FOREGROUND = 0x48
    UI_GLOW = 0x49


class EmbeddedInfoType(object):
    PLAYER_NAME = 0x01
    ITEM_LINK = 0x03
    MAP_POSITION_LINK = 0x04
    QUEST_LINK = 0x05
    STATUS = 0x09
    DALAMUD_LINK = 0x0F
    LINK_TERMINATOR = 0xCF