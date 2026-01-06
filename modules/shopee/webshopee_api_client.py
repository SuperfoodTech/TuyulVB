"""
Copyright (c) 2025 PT Mega SuperFood Nusantara
All rights reserved.

CONFIDENTIAL AND PROPRIETARY INFORMATION

This software and associated documentation files (the "Software") are the
proprietary and confidential information of PT Mega SuperFood Nusantara.

RESTRICTIONS:
- You may not use, copy, modify, merge, publish, distribute, sublicense,
  and/or sell copies of the Software without prior written permission.
- Unauthorized use, reproduction, or distribution is strictly prohibited.
- This Software is provided for authorized use only.

For licensing inquiries, contact: legal@superfoodapp.id

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""

from typing import Dict, Optional, List, Tuple
import json
from config.settings import logging as log
from app.utils.requests_session import BaseAiohttpSession
import random
import base64
import asyncio
from cachetools import TTLCache
import config.settings as config

class WebShopeeAPIClient(BaseAiohttpSession):
    def __init__(self, base_url: str = "https://shopee.co.id"):
        super().__init__(base_url=base_url)
        self.cookie_cache = TTLCache(maxsize=2000, ttl=config.COOKIE_CACHE_TTL)
        self.request_semaphore = asyncio.Semaphore(config.API_MAX_CONCURRENT_REQUESTS)
        self.connection_timeout = config.API_REQUEST_TIMEOUT["connection"]
        self.read_timeout = config.API_REQUEST_TIMEOUT["read"]
        self.total_timeout = config.API_REQUEST_TIMEOUT["total"]

    async def get_order_details(
        self, merchant_id: str, order_id: str, store_id: str, tob_token: str
    ) -> Optional[Dict]:
        """Get order details from Shopee Food API with retry logic"""
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for get_order_details.")
            return {"code": 0, "data": {"order_id": order_id, "message": "Simulated success (DRY_RUN)"}}
        
        retry_count = 0

        while retry_count < config.API_RETRY_ATTEMPTS:
            try:
                headers = self._get_headers_food(tob_token, store_id)
                async with self.request_semaphore:
                    async with self:
                        url = f"/api/seller/new-orders/{order_id}"
                        response = await self.get(
                            url, headers=headers, timeout=self.total_timeout
                        )
                        if response and response.get("code") == 0:
                            return response
                        elif response and response.get("code") in [401, 403]:
                            log.error(f"Authentication failed for order {order_id}")
                            return None

                retry_count += 1
                if retry_count < config.API_RETRY_ATTEMPTS:
                    await asyncio.sleep(config.API_BASE_RETRY_DELAY * (2**retry_count))

            except Exception as e:
                log.error(
                    f"Failed to fetch order details for order {order_id}: {str(e)}"
                )
                retry_count += 1
                if retry_count < config.API_RETRY_ATTEMPTS:
                    await asyncio.sleep(config.API_BASE_RETRY_DELAY * (2**retry_count))

        return None

    def _get_shopee_tob_token(self, cookie_data: List[Dict]) -> Optional[str]:
        """Extract shopee_tob_token from cookie data"""
        if isinstance(cookie_data, str):
            try:
                cookie_data = json.loads(cookie_data)
            except json.JSONDecodeError:
                log.error("Failed to parse cookie data as JSON")
                return None

        if isinstance(cookie_data, list):
            for cookie in cookie_data:
                if (
                    isinstance(cookie, dict)
                    and cookie.get("name") == "shopee_tob_token"
                ):
                    return cookie.get("value")
        return None

    def _get_headers_food(self, tob_token: str, entity_id: str) -> Dict[str, str]:
        """Generate headers for Food API requests."""
        return {
            "Host": "foody.shopee.co.id",
            "Accept": "application/json, text/plain, */*",
            "Cookie": f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token}",
            "X-Sf-Platform": "2",
            "Operate-Source": "partnerapp",
            "User-Agent": "language=id app_type=2 shopee-partner appver=33501 "
            "(iOS 18.0.1) secid=4002 food_rn_ver=4261 spp_rn_ver=4297 "
            "language=id app_type=2 shopee-partner appver=33501 "
            "(iOS 18.0.1) Cronet/102.0.5005.61",
            "Accept-Language": "id-ID,id,en-US,en",
        }

    def _get_headers_notification(self, tob_token: str) -> Dict[str, str]:
        """Generate headers for Notification API requests."""
        return {
            "Host": "shopee.co.id",
            "Cookie": f"shopee_tob_token={tob_token};",
            "A-Os": "ios",
            "User-Agent": "app_type=2  CFNetwork client_platform=Beeshop  appver=33501",
            "Accept-Language": "id-ID,id;q=0.9",
            "A-Lang": "id",
            "X-Merchant-Timezone": "Asia/Jakarta",
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
        }

    def _get_headers_notification_content(self, tob_token: str) -> Dict[str, str]:
        """Generate headers for Notification Content API requests."""
        return {
            "Host": "shopee.co.id",
            "Cookie": f"shopee_tob_token={tob_token};",
            "Content-Type": "application/json",
            "X-Merchant-From": "3",
            "Accept": "*/*",
            "X-Merchant-Timezone": "Asia/Jakarta",
            "A-Appversion": "3.35.1",
            "A-Os": "ios",
            "A-Lang": "id",
        }

    async def get_order_details(
        self,
        merchant_id: str,
        order_id: str,
        store_id: str,
        tob_token: str,
    ) -> Optional[Dict]:
        """Get order details from Shopee Food API"""
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for get_order_details.")
            return {"code": 0, "data": {"order_id": order_id, "message": "Simulated success (DRY_RUN)"}}
        
        try:
            headers = self._get_headers_food(tob_token, store_id)
            async with self.request_semaphore:
                url = f"/api/seller/new-orders/{order_id}"
                response = await self.get(
                    url, headers=headers
                )  # Removed timeout parameter
                if response and response.get("code") == 0:
                    return response
                elif response and response.get("code") in [401, 403]:
                    log.error(f"Authentication failed for order {order_id}")
                    return None
        except Exception as e:
            log.error(f"Failed to fetch order details for order {order_id}: {str(e)}")
            return None

    async def get_store_dishes(
        self,
        merchant_id: str,
        store_id: str,
        tob_token: str,
    ) -> Optional[Dict]:
        """Get store dishes information from Shopee Food API"""
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for get_store_dishes.")
            return {"dishes": [], "message": "Simulated success (DRY_RUN)"}
        
        try:
            headers = self._get_headers_food(tob_token, store_id)
            async with self.request_semaphore:
                async with self:
                    url = "/api/seller/store/dishes"
                    response = await self.get(
                        url, headers=headers, timeout=self.total_timeout
                    )
                    if response and response.get("code") == 0:
                        return response.get("data")
                    return None
        except Exception as e:
            log.error(f"Failed to fetch store dishes for store {store_id}: {str(e)}")
            return None

    async def get_notifications(
        self, account_id: str, tob_token: str
    ) -> Tuple[List[Dict], str]:
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for get_notifications.")
            return ([], tob_token)
        
        headers = self._get_headers_notification(tob_token)
        payload = {
            "hasLastActionId": True,
            "hasRequestid": True,
            "hasGroupid": True,
            "hasBffMeta": False,
            "bffMeta": {},
            "hasActionCate": True,
            "action_cate": 33,
            "need_grouped": True,
            "hasNeedGrouped": True,
            "requestid": str(random.randint(1, 100)),
            "last_action_id": 0,
            "groupid": 0,
            "request_number": 20,
            "hasRequestNumber": True,
        }

        # Remove timeout parameter from post call
        response = await self.post(
            "api/v4/notification/get_action_id_list", json=payload, headers=headers
        )
        notifications = response.get("data", {}).get("simple_action_list", [])
        return notifications, tob_token

    async def get_notification_content(self, action_id: int, tob_token: str) -> Dict:
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for get_notification_content.")
            return {"action_id": action_id, "content": "Simulated content (DRY_RUN)"}
        
        headers = self._get_headers_notification_content(tob_token)
        payload = {
            "hasRequestid": False,
            "requestid": str(random.randint(1, 100)),
            "actionid_list": [action_id],
            "actionidListArray_Count": 1,
            "hasBffMeta": False,
            "bffMeta": {},
        }

        # Remove timeout parameter from post call
        response = await self.post(
            "api/v4/notification/get_action_content_list", json=payload, headers=headers
        )
        content_list = response.get("data", {}).get("action_content_list", [])
        return content_list[0] if content_list else {}

    @staticmethod
    def decode_base64(encoded_string: str) -> str:
        """Decode base64 encoded string"""
        try:
            return base64.b64decode(encoded_string).decode("utf-8")
        except:
            return encoded_string

    @staticmethod
    def extract_order_details(action_redirect_url: str) -> Optional[Dict[str, str]]:
        """Extract order_id and store_id from action_redirect_url"""
        try:
            query_params = dict(
                param.split("=")
                for param in action_redirect_url.split("?")[1].split("&")
            )
            return {
                "order_id": query_params.get("orderId"),
                "store_id": query_params.get("storeId"),
            }
        except Exception as e:
            log.error(f"Failed to extract order details: {e}")
            return None

    async def get_menu_items(
        self,
        tob_token: str,
        entity_id: str,
    ) -> Optional[Dict]:
        """Get menu items from Shopee Food API"""
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for get_menu_items.")
            return {"items": [], "message": "Simulated success (DRY_RUN)"}
        
        try:
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                "Cookie": f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token};",
                "Origin": "https://partner.shopee.co.id",
                "Referer": "https://partner.shopee.co.id/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15",
            }

            async with self.request_semaphore:
                async with self:
                    url = "/api/seller/store/dishes"
                    response = await self.get(
                        url, headers=headers, timeout=self.total_timeout
                    )
                    if response and response.get("code") == 0:
                        return response.get("data")
                    return None
        except Exception as e:
            log.error(f"Failed to fetch menu items: {str(e)}")
            return None

    async def get_shopee_modifiers(
        self, tob_token: str, entity_id: str, dish_shopee_id: str
    ) -> Optional[Dict]:
        """Get modifiers for a specific dish from Shopee Food API"""
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for get_shopee_modifiers.")
            return {"modifiers": [], "message": "Simulated success (DRY_RUN)"}
        
        try:
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                "Cookie": f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token};",
                "Origin": "https://partner.shopee.co.id",
                "Referer": "https://partner.shopee.co.id/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15",
            }

            async with self.request_semaphore:
                async with self:
                    url = f"/api/seller/dishes/{dish_shopee_id}/option-groups"
                    response = await self.get(
                        url, headers=headers, timeout=self.total_timeout
                    )
                    if response and response.get("code") == 0:
                        return response.get("data")
                    return None
        except Exception as e:
            log.error(f"Failed to fetch modifiers for dish {dish_shopee_id}: {str(e)}")
            return None

    async def get_shopee_operational_hours(
        self, tob_token: str, entity_id: str
    ) -> Optional[Dict]:
        """Get store operational hours from Shopee Food API"""
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for get_shopee_operational_hours.")
            return {"regular_hours": {}, "message": "Simulated success (DRY_RUN)"}
        
        try:
            headers = {
                "Host": "foody.shopee.co.id",
                "Accept": "application/json, text/plain, */*",
                "X-Sf-Platform": "2",
                "Operate-Source": "partnerapp",
                "User-Agent": "language=id app_type=2 shopee-partner appver=33600 (iOS 18.0.1) secid=4002 food_rn_ver=4467 spp_rn_ver=4391 language=id app_type=2 shopee-partner appver=33600 (iOS 18.0.1) Cronet/102.0.5005.61",
                "Accept-Language": "id-ID,id,en-US,en",
                "Cookie": f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token};",
            }

            async with self.request_semaphore:
                async with self:
                    url = "/api/seller/store/regular-hours"
                    response = await self.get(
                        url, headers=headers, timeout=self.total_timeout
                    )
                    if response and response.get("code") == 0:
                        return response.get("data")
                    return None
        except Exception as e:
            log.error(
                f"Failed to fetch operational hours for store {entity_id}: {str(e)}"
            )
            return None

    async def update_shopee_operational_hours(
        self, tob_token: str, entity_id: str, regular_hours: Dict
    ) -> bool:
        """Update store operational hours in Shopee Food API"""
        if config.DRY_RUN:
            log.warning(f"DRY_RUN ENABLED: Skipping ASYNC Shopee API call for update_shopee_operational_hours.")
            return True
        
        try:
            headers = {
                "Host": "foody.shopee.co.id",
                "Accept": "application/json, text/plain, */*",
                "X-Sf-Platform": "2",
                "Operate-Source": "partnerapp",
                "User-Agent": "language=id app_type=2 shopee-partner appver=33600 (iOS 18.0.1) secid=4002 food_rn_ver=4467 spp_rn_ver=4391 language=id app_type=2 shopee-partner appver=33600 (iOS 18.0.1) Cronet/102.0.5005.61",
                "Accept-Language": "id-ID,id,en-US,en",
                "Cookie": f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token};",
                "Content-Type": "application/json",
            }

            payload = {"regular_hours": regular_hours}

            async with self.request_semaphore:
                async with self:
                    url = "/api/seller/store/regular-hours"
                    # Remove timeout parameter
                    response = await self.post(url, json=payload, headers=headers)
                    # save response to file
                   
                    if response and response.get("code") == 0:
                        return True
                    log.error(
                        f"Failed to update operational hours for store {entity_id}: {response}"
                    )
                    return False
        except Exception as e:
            log.error(
                f"Failed to update operational hours for store {entity_id}: {str(e)}"
            )
            return False


    async def cancel_order_shopee(
            self,
            order_id: str,
            tob_token: str,
            entity_id: str,
            cancel_reason: int = 10017,
            cancel_remark: str = "",
            operation: int = 1
        ) -> bool:
            """Cancel order in Shopee Food API"""
            try:
                headers = {
                    "Host": "foody.shopee.co.id",
                    "Content-Type": "application/json;charset=utf-8",
                    "Accept": "application/json, text/plain, */*",
                    "X-Sf-Platform": "2",
                    "Operate-Source": "partnerapp",
                    "User-Agent": "language=id app_type=2 shopee-partner appver=34400 (iOS 18.0.1) secid=4002 food_rn_ver=5267 spp_rn_ver=5188 language=id app_type=2 shopee-partner appver=34400 (iOS 18.0.1) Cronet/102.0.5005.61",
                    "Accept-Language": "id-ID,id,en-US,en",
                    "Cookie": f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token};"
                }

                payload = {
                    "cancel_reason": cancel_reason,
                    "cancel_remark": cancel_remark,
                    "operation": operation
                }

                async with self.request_semaphore:
                    async with self:
                        url = f"/api/seller/orders/{order_id}/action/cancel"
                        response = await self.post(url, json=payload, headers=headers)
                        if response and response.get("code") == 0:
                            return True
                        log.error(
                            f"Failed to cancel order {order_id}: {response}"
                        )
                        return False
            except Exception as e:
                log.error(
                    f"Failed to cancel order {order_id}: {str(e)}"
                )
                return False


    async def ready_order_shopee(
            self,
            order_id: str,
            tob_token: str,
            entity_id: str
        ) -> bool:
            """Mark order as ready in Shopee Food API"""
            try:
                headers = {
                    "Host": "foody.shopee.co.id",
                    "Accept": "application/json, text/plain, */*",
                    "X-Sf-Platform": "2",
                    "Operate-Source": "partnerapp",
                    "User-Agent": "language=id app_type=2 shopee-partner appver=34400 (iOS 18.0.1) secid=4002 food_rn_ver=5267 spp_rn_ver=5284 language=id app_type=2 shopee-partner appver=34400 (iOS 18.0.1) Cronet/102.0.5005.61",
                    "Accept-Language": "id-ID,id,en-US,en",
                    "Cookie": f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token};"
                }

                async with self.request_semaphore:
                    async with self:
                        url = f"/api/seller/orders/{order_id}/action/ready"
                        response = await self.post(url, headers=headers)
                        if response and response.get("code") == 0:
                            return True
                        log.error(
                            f"Failed to mark order {order_id} as ready: {response}"
                        )
                        return False
            except Exception as e:
                log.error(
                    f"Failed to mark order {order_id} as ready: {str(e)}"
                )
                return False