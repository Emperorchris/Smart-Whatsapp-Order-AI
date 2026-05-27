import enum


class MessageType(enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    UNDELIVERED = "undelivered"


class ConversationStatus(enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"


class ConversationType(enum.Enum):
    ONE_TO_ONE = "one_to_one"
    GROUP = "group"
    CHANNEL = "channel"
    CUSTOMER_SERVICE = "customer_service"
    AI_KNOWLEDGE_BASED = "ai_knowledge_based"


class MessageDirection(enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CustomerSegment(enum.Enum):
    NEW = "new"
    RETURNING = "returning"
    VIP = "vip"
    CHURNED = "churned"


class CustomerStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"


class CustomerType(enum.Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"


class CartStatus(enum.Enum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    ABANDONED = "abandoned"


class OrderStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PaymentMethod(enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cash_on_delivery"


class StaffRole(enum.Enum):
    ADMIN = "admin"
    SUPPORT = "support"
    SALES = "sales"


class CartActionType(enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"
    VIEW = "view"
    CLEAR = "clear"


class HandOffStatus(enum.Enum):
    NONE = "none"
    PENDING = "pending"
    CANCELLED = "cancelled"
    REQUESTED = "requested"
    ACTIVE = "active"
    RESOLVED = "resolved"


class HandOffTriggeredBy(enum.Enum):
    AI = "ai"
    CUSTOMER = "customer"
    STAFF = "staff"
    RULE = "rule"


class MessageSenderType(enum.Enum):
    CUSTOMER = "customer"
    AI = "ai"
    STAFF = "staff"
    TOOL = "tool"


class StaffConversationCommand(enum.Enum):
    NEXT = "#next"
    DONE = "#done"
    QUEUE = "#queue"
    SKIP = "#skip"
    INFO = "#info"
    
    
    
class GraphNodeName(enum.Enum):
    CART_NODE = "cart_node"
    CUSTOMER_NODE = "customer_node"
    HANDOFF_NODE = "handoff_node"
    PRODUCT_LOOKUP_NODE = "product_lookup_node"
    ROUTER_NODE = "router_node"
    ROUTE_BY_INTENT = "route_by_intent_node"
    ORDER_NODE = "order_node"
    PAYMENT_NODE = "payment_node"
    
    
class IntentName(enum.Enum):
    PRODUCT_INQUIRY = "product_inquiry"
    CART = "cart"
    ORDER = "order"
    HANDOFF = "handoff"
    CHITCHAT = "chitchat"



class OrderActionType(enum.Enum):
    PLACE_ORDER = "place_order"
    CHECK_STATUS = "check_status"
    CANCEL_ORDER = "cancel_order"
    
    
class DeliveryStatus(enum.Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURNED = "returned"


class AddressLabel(enum.Enum):
    HOME = "home"
    OFFICE = "office"
    SHOP = "shop"
    OTHER = "other"