import enum


class MessageType(enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"


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


class StaffConversationCommand(enum.Enum):
    NEXT = "#next"
    DONE = "#done"
    QUEUE = "#queue"
    SKIP = "#skip"
    INFO = "#info"