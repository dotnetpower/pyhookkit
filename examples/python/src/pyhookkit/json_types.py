"""JSON-compatible value types shared by outbound ports and adapters."""

type JsonValue = (
    str | int | float | bool | list["JsonValue"] | dict[str, "JsonValue"] | None
)
type JsonObject = dict[str, JsonValue]
