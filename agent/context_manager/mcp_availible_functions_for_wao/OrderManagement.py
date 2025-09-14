import asyncio
import datetime
import glob
import json
import os.path
import random
import shutil
import signal
import time
from os import PathLike
from typing import Optional, Dict, List, Any

from pynput import keyboard

from LLM_Module.Wao_Order.Wao import WaoOrderController


# --- Snowflake ID 生成器类 ---
# 这是一个简化的 Snowflake 实现,by gulee
# 在生产环境中，推荐使用功能更完善的现成库。
class Snowflake:
    def __init__(self, worker_id: int, epoch: int = 1672531200000):  # 2023-01-01 00:00:00 UTC
        self.worker_id = worker_id
        self.epoch = epoch
        self.sequence = 0
        self.last_timestamp = -1

        self.worker_id_bits = 10
        self.sequence_bits = 12

        self.max_worker_id = (1 << self.worker_id_bits) - 1
        self.max_sequence = (1 << self.sequence_bits) - 1

        if self.worker_id > self.max_worker_id or self.worker_id < 0:
            raise ValueError(f"Worker ID must be between 0 and {self.max_worker_id}")

    def generate(self) -> int:
        timestamp = self.get_timestamp_ms()

        if timestamp < self.last_timestamp:
            raise Exception("Clock moved backwards. Refusing to generate ID.")

        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & self.max_sequence
            if self.sequence == 0:
                timestamp = self.wait_until_next_ms(self.last_timestamp)
        else:
            self.sequence = 0

        self.last_timestamp = timestamp

        timestamp_part = (timestamp - self.epoch) << (self.worker_id_bits + self.sequence_bits)
        worker_id_part = self.worker_id << self.sequence_bits

        return timestamp_part | worker_id_part | self.sequence

    @staticmethod
    def get_timestamp_ms() -> int:
        return int(time.time() * 1000)

    def wait_until_next_ms(self, last_timestamp: int) -> int:
        timestamp = self.get_timestamp_ms()
        while timestamp <= last_timestamp:
            timestamp = self.get_timestamp_ms()
        return timestamp


class FakeWebsocket:
    # This is a fake websocket holder, jik OrderManagement.hot_reload_send_method(func) not used
    @staticmethod
    async def send(message):
        print(f"fake_websocket.send: {message[10:]}")


class HandHoldManager:
    def __init__(self, send):
        self.isShowingQRCode = False
        self.send = send

    def hot_reload(self, send):
        self.send = send

    async def drop_hand(self):
        if not self.isShowingQRCode:
            return
        self.isShowingQRCode = False
        await self.send(f"SWITCH_ACTION:{json.dumps({'IsCollectingPayCode': False, 'IsPuttingDownPayCode': True})}")

    async def raise_hand(self):
        if self.isShowingQRCode:
            return
        self.isShowingQRCode = True
        await self.send(f"SWITCH_ACTION:{json.dumps({'IsCollectingPayCode': True, 'IsPuttingDownPayCode': False})}")


class OrderManagement:
    def __init__(self, _wao_order_controller: WaoOrderController):
        """
        初始化 OrderManagement 实例。
        传入自定义的有效属性配置。
        """

        self.wao_order_controller = _wao_order_controller
        self.id_generator = Snowflake(worker_id=1)
        self.isShowingMenu = False
        self.QRCODE_PATH = "/home/gulee/Downloads/YuMi_20250814_Linux_01_Pre/_ExternalData/Payment_.jpg"
        assert os.path.exists(self.QRCODE_PATH.removesuffix("/Payment_.jpg")), "那是个硬编码，你最好改掉它"

        menu_items = self.wao_order_controller.get_products_list()
        self.AVAILABLE_PRODUCTS_ENUM = {key: value.get("id") for key, value in menu_items.items()}

        self.AVAILABLE_CONCENTRATIONS_ENUM = {
            '100%': 56821134,
            '60%': 56821135,
            '30%': 56821136,
            '150%': 56821137
        }

        self.AVAILABLE_SUGAR_LEVELS_ENUM = {
            '少糖': 56821138,
            '正常糖': 56821139,
            '多糖': 56821140,
            '无糖': 56821141
        }

        self.AVAILABLE_TEMPERATURES_ENUM = {
            '少冰': 56821142,
            '正常冰': 56821143,
            '飞冰': 56821144,
            '温热': 56821145
        }

        self.valid_attributes = {
            # '品名':{"爽脆马蹄冻冻茶","云春素月鲜奶茶","奇岩幽兰鲜奶茶"},
            '品名': self.AVAILABLE_PRODUCTS_ENUM.keys(),
            '浓度': self.AVAILABLE_CONCENTRATIONS_ENUM.keys(),
            '甜度': self.AVAILABLE_SUGAR_LEVELS_ENUM.keys(),
            '温度': self.AVAILABLE_TEMPERATURES_ENUM.keys(),
        }

        # 订单结构更新为支持多杯奶茶
        self._current_order_in_session = {}

        self.fake_websocket = FakeWebsocket()
        self._send = self.fake_websocket.send

        self.hand_hold = HandHoldManager(self._send)

    def hot_reload_send_method(self, websocket_send):
        """
        for hot-reload _send() when ChatSession() init. before that, we use FakeWebsocket() as a placeholder
        """
        self._send = websocket_send
        self.hand_hold.hot_reload(websocket_send)

    def get_valid_attributes(self):
        return self.valid_attributes

    @staticmethod
    def _save_order_to_db(order_json: dict, status: str):
        """
        [内部函数] 模拟将订单保存到数据库。
        """
        order_json_copy = order_json.copy()
        order_json_copy["_status"] = status
        order_json_copy["_timestamp"] = datetime.datetime.now().isoformat()
        if "_order_id" not in order_json_copy or order_json_copy["_order_id"] is None:
            order_json_copy["_order_id"] = str(order_json_copy.get("_order_id", "无ID"))
        print(f"[DB] 订单 {order_json_copy['_order_id']} 已保存，状态: {status}")

    def _format_order_for_wao(self, order_json: dict) -> List[Dict[str, Dict[str, Any]]]:
        """
        将内部订单格式转换为Wao所需的格式，每个item为一个独立字典，键是商品ID。
        同时将字符串属性翻译为对应的数字ID。
        """
        wao_formatted_items = []
        for item in order_json.get("items", []):
            item_name = item.get("品名")

            # 查找商品ID
            item_id = self.AVAILABLE_PRODUCTS_ENUM.get(item_name)

            if item_id:
                # 翻译属性值为对应的数字ID
                concentration_id = self.AVAILABLE_CONCENTRATIONS_ENUM.get(item.get("浓度"))
                sugar_level_id = self.AVAILABLE_SUGAR_LEVELS_ENUM.get(item.get("甜度"))
                temperature_id = self.AVAILABLE_TEMPERATURES_ENUM.get(item.get("温度"))

                # 检查所有属性是否都已翻译
                if all([concentration_id, sugar_level_id, temperature_id]):
                    wao_formatted_items.append({
                        str(item_id): {
                            "浓度": str(concentration_id),
                            "甜度": str(sugar_level_id),
                            "温度": str(temperature_id),
                            "数量": 1,  # 数量固定为1
                        }
                    })
                else:
                    print(f"[ERROR] 无法为商品 '{item_name}' 翻译所有属性。请检查订单数据完整性。")
        return wao_formatted_items

    def _send_order_to_terminal(self, order_json: dict) -> tuple[tuple[Any, Any, Any], str]:
        """
        [内部函数] 模拟发送订单到点单端。
        """
        wao_formatted_order = self._format_order_for_wao(order_json)
        recv_tuple, payment_qrcode_path = self.wao_order_controller.submit(item_list=wao_formatted_order,
                                                                           pickup_id=self.id_generator.generate())

        # recv_tuple: (pickup_id, order_id, payitem_id)
        # print("\ndebug:")
        # print(f"[API] 订单 {order_json.get('_order_id', '')} 已发送，内容：")
        # print(f"  {json.dumps(wao_formatted_order, ensure_ascii=False, indent=2)}")
        return recv_tuple, payment_qrcode_path

    async def _periodic_check_if_order_paid(self, _stop_event, _id_tuple, threshold: int):
        """
        async handler for periodic check payment status,
        30s timeout,
        query per 1s, stop when stop_event set(result=True)
        """

        def check_if_order_paid(id_tuple, time_spent):
            """
            subfunction for check payment status
            call wao backend to check if order is paid
            :return: True if paid, False if not paid or error
            """
            ret = self.wao_order_controller.query_order_status(id_tuple)
            print(f"debug: check_if_order_paid({id_tuple}), waited {time_spent} s, 30 s limited")

            if ret is None:
                raise Exception("Fatal error: query_order_status return None, unknown error")

            return ret

        time_spent = 0
        while not (_stop_event.is_set() or time_spent >= threshold):
            try:
                time_spent += 1
                result = check_if_order_paid(id_tuple=_id_tuple, time_spent=time_spent)
                if result:
                    print("函数返回True，定时任务结束")
                    return "paid"
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                print("定时任务被取消")
                raise
        print("定时任务被外部停止")
        raise asyncio.CancelledError()

    async def _keyboard_listener_async(self, _stop_event):
        """
        异步包装器，使用非阻塞方式监听键盘事件。
        """
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()

        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    print(f"\n检测到ESC键，准备退出...")
                    # 将结果放入队列
                    loop.call_soon_threadsafe(queue.put_nowait, "esc_pressed")
                    return False  # 停止监听器
            except Exception as e:
                print(f"按键处理错误: {e}")
                loop.call_soon_threadsafe(queue.put_nowait, "listener_error")
                return False

        def on_release(key):
            pass

        print("全局键盘监听器已启动...")
        print("按下ESC键退出程序：")
        print("注意：即使终端失去焦点，热键依然有效！")

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        # 监听器本身就是非阻塞的，只需启动即可
        listener.start()

        try:
            # 阻塞在此，等待队列中出现结果
            result = await queue.get()
            return result
        except asyncio.CancelledError:
            print("键盘监听器任务被取消")
            raise
        finally:
            # 确保无论如何，监听器都会停止
            if listener.is_alive():
                listener.stop()

    async def _wait_until_paid_or_time_passed(self, recv_tuple) -> bool:
        """
        同时运行定时任务和全局键盘监听，任何一个完成就停止另一个
        等待订单支付或 30s 超时。
        :return: True if paid, False if timed out.
        """
        # 创建一个停止事件，用于线程间通信
        stop_event_for_keyboard_and_payment_status_check = asyncio.Event()

        # 设置信号处理器（用于Ctrl+C）
        def signal_handler(sig, frame):
            print("\n收到中断信号，正在停止...")
            stop_event_for_keyboard_and_payment_status_check.set()

        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)

        result = False
        try:
            # 创建两个任务
            task1 = asyncio.create_task(
                self._periodic_check_if_order_paid(stop_event_for_keyboard_and_payment_status_check,
                                                   _id_tuple=recv_tuple, threshold=45))
            task2 = asyncio.create_task(
                self._keyboard_listener_async(stop_event_for_keyboard_and_payment_status_check))

            # 等待任何一个任务完成
            done, pending = await asyncio.wait(
                [task1, task2],
                return_when=asyncio.FIRST_COMPLETED
            )

            # 设置停止事件，确保所有任务都能收到停止信号
            stop_event_for_keyboard_and_payment_status_check.set()

            # 取消剩余的任务
            for task in pending:
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            # 获取完成任务的结果
            # "paid" if paid
            # "esc_pressed" if ESC key pressed, basically because of manual cancellation
            completed_task = done.pop()
            try:
                result = await completed_task
            except asyncio.CancelledError:
                result = "cancelled"

            print("=" * 60)
            print(f"程序结束，原因: {result}")

        except KeyboardInterrupt:
            print("\n程序被Ctrl+C中断")
            stop_event_for_keyboard_and_payment_status_check.set()
        except Exception as e:
            print(f"程序发生错误: {e}")
            import traceback
            traceback.print_exc()
            stop_event_for_keyboard_and_payment_status_check.set()
        finally:
            return result == "paid"

    async def _call_unity_to_show_qrcode(self, payment_qrcode_path: PathLike | str | bytes):

        """
        Args:
            payment_qrcode_path: PathLike | str | bytes, path to payment qrcode image file, should be abs
        """
        await self.hand_hold.drop_hand()
        shutil.copy(payment_qrcode_path, self.QRCODE_PATH)
        await self.hand_hold.raise_hand()
        await self._send(f"SWITCH_ACTION:{json.dumps({'IsCollectingPayCode': True})}")

    def initialize_an_order(self,
                            name: Optional[str] = None,
                            concentration: Optional[str] = None,
                            sugar_level: Optional[str] = None,
                            temperature: Optional[str] = None) -> dict:
        """
        初始化一个新的奶茶订单。可选择性地在初始化时添加第一杯奶茶。

        Args:
            name (str, optional): 奶茶的品名。如果提供，将在初始化时添加这杯奶茶。
            concentration (str, optional): 浓度级别。
            sugar_level (str, optional): 甜度级别。
            temperature (str, optional): 温度级别。

        Returns:
            dict: 新初始化的订单 JSON 对象。
        """
        if self._current_order_in_session and \
                self._current_order_in_session.get("_status") == "in_progress":
            self._save_order_to_db(self._current_order_in_session, "abnormal_interrupted")
            print("[ORDER_FUNC] 检测到前一个未完成订单，已标记为异常并清空。")

        new_order_id = self.id_generator.generate()
        self._current_order_in_session = {
            "items": [],
            "_order_id": new_order_id,
            "_status": "in_progress"
        }

        # 如果提供了奶茶品名，则在初始化时添加第一杯奶茶
        if name:
            # 验证品名是否有效
            if name not in self.valid_attributes.get("品名", []):
                print(f"[ERROR] 无效的品名: '{name}'。请从菜单中选择。")
                print("[ORDER_FUNC] 订单已初始化但未添加奶茶。")
            else:
                # 添加第一杯奶茶
                new_item = {
                    "品名": name,
                    "浓度": concentration,
                    "甜度": sugar_level,
                    "温度": temperature,
                }
                self._current_order_in_session["items"].append(new_item)
                print(f"[ORDER_FUNC] 已初始化新订单 (ID: {new_order_id}) 并添加奶茶：'{name}'")
        else:
            print(f"[ORDER_FUNC] 已初始化新订单 (ID: {new_order_id})，暂未添加任何奶茶。")

        self._save_order_to_db(self._current_order_in_session, "in_progress")
        return self._current_order_in_session

    def display_menu(self):
        """
        展示当前的菜单内容给顾客。

        此函数旨在响应顾客关于菜单的询问，提供详细的饮品、小吃和甜点列表及其简要描述。
        大模型可以调用此函数来获取菜单信息，然后将信息呈现给顾客（例如，通过语音或屏幕显示）。
        """
        print("\n[CUSTOMER_MGMT] 正在展示菜单...")
        menu_output = "我们有以下饮品和选项：\n"
        for attribute, values in self.valid_attributes.items():
            menu_output += f"  - **{attribute}**: {', '.join(values)}\n"
        print(menu_output)

    def add_order_item(self,
                       name: str,
                       concentration: Optional[str] = None,
                       sugar_level: Optional[str] = None,
                       temperature: Optional[str] = None) -> dict:
        """
        向当前订单中添加一杯新的奶茶。

        Args:
            name (str): 奶茶的品名。
            concentration (str, optional): 浓度级别。
            sugar_level (str, optional): 甜度级别。
            temperature (str, optional): 温度级别。

        Returns:
            dict: 包含新添加奶茶的当前订单 JSON 对象。
        """
        if self._current_order_in_session == {} or \
                self._current_order_in_session.get("_status") != "in_progress":
            print("[ORDER_FUNC] 当前无进行中的订单，正在初始化新订单...")
            self.initialize_an_order()

        if name not in self.valid_attributes.get("品名", []):
            print(f"[ERROR] 无效的品名: '{name}'。请从菜单中选择。")
            return self._current_order_in_session

        new_item = {
            "品名": name,
            "浓度": concentration,
            "甜度": sugar_level,
            "温度": temperature,
        }
        self._current_order_in_session["items"].append(new_item)
        print(f"[ORDER_FUNC] 已向订单 (ID: {self._current_order_in_session['_order_id']}) 添加新奶茶：'{name}'")
        return self._current_order_in_session

    def modify_order_attribute(self, attributes_to_modify: Dict[str, str], item_index: int = 0) -> dict:
        """
        一次修改当前奶茶订单中的一个或多个指定属性。

        Args:
            attributes_to_modify (dict): 包含要修改的属性名和新值的字典，
                                         例如：{'品名': '奶茶A', '甜度': '正常糖'}。
            item_index (int, optional): 要修改的特定奶茶的索引（从0开始）。如果未提供，默认为0。

        Returns:
            dict: 更新后的订单 JSON 对象。如果任何一个属性名或值无效，则返回未修改的订单。
        """
        if (isinstance(attributes_to_modify, str)
                and attributes_to_modify.startswith('{')
                and attributes_to_modify.endswith('}')):
            attributes_to_modify = json.loads(attributes_to_modify)

        if self._current_order_in_session == {} or not self._current_order_in_session.get("items"):
            print("[ERROR] 当前没有进行中的订单或订单中没有奶茶可供修改。")
            return self._current_order_in_session

        if not (0 <= item_index < len(self._current_order_in_session["items"])):
            print(f"[ERROR] 无效的奶茶索引: '{item_index}'。")
            return self._current_order_in_session

        target_item = self._current_order_in_session["items"][item_index]

        # 批量验证
        for attribute_name, attribute_value in attributes_to_modify.items():
            if attribute_name not in self.valid_attributes:
                print(f"[ERROR] 无效的属性名: '{attribute_name}'。可用属性: {list(self.valid_attributes.keys())}")
                return self._current_order_in_session
            if attribute_value not in self.valid_attributes[attribute_name]:
                valid_values_str = ", ".join(self.valid_attributes[attribute_name])
                print(f"[ERROR] 属性 '{attribute_name}' 的值 '{attribute_value}' 不合法。有效值: {valid_values_str}")
                return self._current_order_in_session

        # 批量修改
        for attribute_name, attribute_value in attributes_to_modify.items():
            target_item[attribute_name] = attribute_value
            print(f"[ORDER_FUNC] 已更新第 {item_index + 1} 杯奶茶的属性: {attribute_name} = {attribute_value}")

        return self._current_order_in_session

    async def _play_voice_message(self, opt):
        if opt == "PLEASE_PAY":
            path_ = "/home/gulee/Documents/GitHub/hikari_mirror/LLM_Module/agent/src/audio_src/扫码支付/*"
        elif opt == "THANK_YOU":
            path_ = "/home/gulee/Documents/GitHub/hikari_mirror/LLM_Module/agent/src/audio_src/付款成功/*"
        else:
            raise ValueError("?")
        assert os.path.exists(path_.removesuffix("/*")), "那是个硬编码，你最好改掉它"
        path_of_audio = random.choice(glob.glob(path_))
        with open(path_of_audio, "rb") as f:
            audio = f.read()
            await self._send(audio)
            print(">>> [主函数] 已发送")

    async def end_conversation_and_place_order(self) -> dict | None:
        """
        当用户确认订单后调用此函数。
        此函数负责检查订单完整性、向后端发送订单、处理支付流程，并接管与用户的后续交互。
        """
        # 1. 检查订单有效性
        if not self._current_order_in_session or \
                self._current_order_in_session.get("_status") not in ["in_progress", "pending_modification",
                                                                      "sent_failed"] or \
                not self._current_order_in_session.get("items"):
            print("[ORDER_FUNC] 无有效订单可发送。请先添加奶茶。")
            # 返回一个包含错误信息的字典，让框架能通知LLM
            return {"error": "无有效订单，请先添加奶茶"}

        # 2. 检查订单完整性
        for i, item in enumerate(self._current_order_in_session["items"]):
            missing_attributes = [attr for attr in self.valid_attributes.keys() if item.get(attr) is None]
            if missing_attributes:
                error_msg = f"订单中的第 {i + 1} 杯奶茶不完整！缺少属性: {', '.join(missing_attributes)}。"
                print(f"[ERROR] {error_msg}")
                # 返回错误信息，让LLM知道需要补充信息
                return {"error": error_msg}

        # 3. 订单完整，准备发送，LLM交互在此终止
        print("[ORDER_FUNC] 订单完整，LLM交互终止，由框架接管后续操作。")

        try:
            # 4. 向后端发送订单
            recv_tuple, payment_qrcode_path = self._send_order_to_terminal(self._current_order_in_session)

            # 5. 处理支付流程（非LLM交互）
            await self._play_voice_message("PLEASE_PAY")
            await self._call_unity_to_show_qrcode(payment_qrcode_path)
            await self._wait_until_paid_or_time_passed(recv_tuple=recv_tuple)
            await self.hand_hold.drop_hand()

            # 6. 支付成功，更新状态
            self._current_order_in_session["_status"] = "completed"
            await self._play_voice_message("THANK_YOU")
            self.discard_current_order()

            # 成功完成所有操作，返回 None 或一个成功状态
            return {"success": True}

        except Exception as e:
            print(f"[ERROR] 订单处理过程中发生异常: {e}")
            # 如果处理中途出错，返回一个失败状态，让框架可以处理
            return {"error": f"订单处理失败，请稍后再试。详细信息：{e}"}

    def discard_current_order(self) -> bool:
        """
        销毁当前正在处理的订单。
        """
        if self._current_order_in_session == {}:
            print("[ORDER_FUNC] 当前没有订单可销毁。")
            return False

        order_id_to_destroy = self._current_order_in_session.get("_order_id", "未知ID")
        # self._save_order_to_db(self._current_order_in_session, "abnormal_destroyed")
        # print(f"[ORDER_FUNC] 订单 (ID: {order_id_to_destroy}) 已标记为 'abnormal_destroyed' 并销毁。")
        self._current_order_in_session = {}
        return True

    def get_current_order_in_session(self) -> dict:
        """
        获取当前正在进行的订单。
        """
        return self._current_order_in_session

    def get_menu_dict(self) -> dict:
        return self.menu_dict
