from typing import Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import customer_address_service, whatsapp_service
from ...db.schemas import customer_address_schema
from ...core import utils


@tool
async def save_delivery_address(
    config: RunnableConfig,
    address_line: str,
    city: str,
    state: str,
    label: str = utils.AddressLabel.HOME.value,
    landmark: Optional[str] = None,
    is_default: bool = False,
) -> str:
    """Save a delivery address for the customer.
    Use this when a customer provides their delivery address.
    label can be: home, office, shop, or other."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    address = await customer_address_service.create_address(
        db,
        customer_address_schema.CustomerAddressSchema(
            customer_id=customer_id,
            label=label,
            address_line=address_line,
            city=city,
            state=state,
            landmark=landmark,
            is_default=is_default,
        ),
    )

    return (
        f"Address saved!\n\n"
        f"• {address.address_line}\n"
        f"• {address.city}, {address.state}\n"
        + (f"• Landmark: {address.landmark}\n" if address.landmark else "")
        + f"• Label: {address.label}"
    )


@tool
async def get_my_addresses(config: RunnableConfig) -> str:
    """Get all saved delivery addresses for the customer.
    Use this when a customer asks to see their saved addresses or wants to pick a delivery address."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    addresses = await customer_address_service.get_addresses_by_customer_id(db, customer_id)

    if not addresses:
        return "You don't have any saved addresses yet. Would you like to add one?"

    lines = []
    for i, addr in enumerate(addresses, 1):
        default_tag = " *(default)*" if addr.is_default else ""
        line = (
            f"{i}. *{addr.label.capitalize()}*{default_tag}\n"
            f"   {addr.address_line}\n"
            f"   {addr.city}, {addr.state}"
        )
        if addr.landmark:
            line += f"\n   Landmark: {addr.landmark}"
        lines.append(line)

    return "Your saved addresses:\n\n" + "\n\n".join(lines)


@tool
async def get_default_address(config: RunnableConfig) -> str:
    """Get the customer's default delivery address.
    Use this when placing an order and the customer hasn't specified an address."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        addr = await customer_address_service.get_default_address(db, customer_id)
    except Exception:
        return "You don't have a default address set. Would you like to add one?"

    return (
        f"Your default address:\n\n"
        f"• {addr.address_line}\n"
        f"• {addr.city}, {addr.state}\n"
        + (f"• Landmark: {addr.landmark}\n" if addr.landmark else "")
    )


@tool
async def set_default_delivery_address(config: RunnableConfig, address_number: int) -> str:
    """Set one of the customer's saved addresses as the default delivery address.
    Use this when a customer wants to change their default address.
    address_number is the position (1, 2, 3...) from the saved addresses list."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    addresses = await customer_address_service.get_addresses_by_customer_id(db, customer_id)

    if not addresses:
        return "You don't have any saved addresses. Would you like to add one first?"

    if address_number < 1 or address_number > len(addresses):
        return f"Invalid selection. You have {len(addresses)} saved address(es). Please pick a number between 1 and {len(addresses)}."

    selected_index = addresses[address_number - 1]

    try:
        await customer_address_service.set_default_address(db, str(selected_index.id))
    except Exception:
        return "Sorry, something went wrong setting your default address. Please try again."

    return (
        f"Default address updated to:\n\n"
        f"• *{selected_index.label.capitalize()}*\n"
        f"• {selected_index.address_line}\n"
        f"• {selected_index.city}, {selected_index.state}"
    )


@tool
async def prompt_address_label(config: RunnableConfig) -> str:
    """Start the address collection flow by sending an interactive list of address labels (Home, Office, Shop, Other).
    Use this when a customer wants to add a new delivery address. This sends a WhatsApp interactive message
    so the customer can tap to select their address type. After they select, ask for the remaining details
    (address_line, city, state, landmark) and then call save_delivery_address."""

    customer_phone = config["configurable"].get("customer_whatsapp_number", "")

    if not customer_phone:
        return "Could not determine customer phone number."

    labels = [member for member in utils.AddressLabel]

    sections = [
        {
            "title": "Address Type",
            "rows": [
                {
                    "id": f"addr_label_{label.value}",
                    "title": label.value.capitalize(),
                }
                for label in labels
            ],
        }
    ]

    await whatsapp_service.send_interactive_list(
        to=customer_phone,
        body="What type of address is this?",
        button_text="Select type",
        sections=sections,
        header="New Delivery Address",
        footer="Step 1 of 2",
    )

    return (
        "I've sent the customer an interactive list to pick their address type (Home, Office, Shop, Other). "
        "Wait for their selection, then ask for the full address details: street address, city, state, and an optional landmark."
    )


address_tools = [save_delivery_address, get_my_addresses, get_default_address, set_default_delivery_address, prompt_address_label]
