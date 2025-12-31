from typing import Dict, Type, Optional, List

from .base_gateway import BasePaymentGateway
from .gateways.payfast_gateway import PayFastGateway
from .gateways.easypaisa_gateway import EasyPaisaGateway
from .gateways.jazzcash_gateway import JazzCashGateway
from .gateways.paypak_gateway import PayPakGateway
from .gateways.stripe_gateway import StripeGateway


class PaymentGatewayFactory:
    """Factory for creating payment gateway instances"""

    _gateways: Dict[str, Type[BasePaymentGateway]] = {
        "payfast": PayFastGateway,
        "easypaisa": EasyPaisaGateway,
        "jazzcash": JazzCashGateway,
        "paypak": PayPakGateway,
        "stripe": StripeGateway,
    }

    _instances: Dict[str, BasePaymentGateway] = {}

    @classmethod
    def register(cls, name: str, gateway_class: Type[BasePaymentGateway]) -> None:
        """Register a new gateway class"""
        cls._gateways[name.lower()] = gateway_class

    @classmethod
    def get_gateway(cls, name: str) -> Optional[BasePaymentGateway]:
        """Get or create a gateway instance"""
        name = name.lower()

        if name not in cls._gateways:
            return None

        if name not in cls._instances:
            gateway = cls._gateways[name]()
            if not gateway.initialize():
                return None
            cls._instances[name] = gateway

        return cls._instances[name]

    @classmethod
    def get_available_gateways(cls) -> List[Dict]:
        """Get list of available (configured) gateways"""
        available = []
        for name, gateway_class in cls._gateways.items():
            gateway = gateway_class()
            if gateway.initialize():
                available.append({
                    "name": name,
                    "title": gateway.gateway_name.replace("_", " ").title(),
                    "flow_type": gateway.flow_type,
                    "currency": gateway.currency,
                    "supports_refund": gateway.supports_refund,
                    "supports_partial_refund": gateway.supports_partial_refund,
                })
        return available

    @classmethod
    def is_gateway_available(cls, name: str) -> bool:
        """Check if a gateway is available and configured"""
        gateway = cls.get_gateway(name)
        return gateway is not None

    @classmethod
    def get_all_gateway_names(cls) -> List[str]:
        """Get list of all registered gateway names"""
        return list(cls._gateways.keys())

    @classmethod
    def clear_instances(cls) -> None:
        """Clear cached gateway instances (useful for testing)"""
        cls._instances.clear()
