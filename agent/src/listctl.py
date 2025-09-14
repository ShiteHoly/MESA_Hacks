import time

class OpenaiMessctl():
    def __init__(self, system_list=[], chat_list=[], send_list=[], definition=[], max_len=50):
        self.definition = definition
        self.system_list = system_list
        self.chat_list = chat_list
        self.send_list = send_list
        self.max_len = max_len
        self.send_list= self.definition + self.system_list + self.chat_list

    def system_list_add(self, mess):
        add_list = {"role": "system", "content": mess}
        self.system_list.append(add_list)
        self.send_list = self.definition + self.system_list + self.chat_list

    def user_list_add(self, mess, role='n'or'a'or'u'):
        if role=="a":
            role="assistant"
        elif role=="u":
            role="user"
            # 4.19暂时注释掉，不注释掉会出现偶尔回复中会带有时间的bug
            #  mess+=time.strftime("%a %b %d %H:%M:%S %Y", time.localtime())

        else:
            raise ValueError("傻逼吧这都能填错")
        add_list = {"role": role, "content": mess}
        self.chat_list.append(add_list)
        if len(self.chat_list) > self.max_len:
            for out_num in range(len(self.chat_list) - self.max_len):
                self.chat_list.pop(out_num)
        self.send_list = self.definition + self.system_list + self.chat_list
        return len(self.chat_list)

    def assistant_stream(self, mess,id):
        self.chat_list[id-1]={'role': 'assistant', 'content': self.chat_list[id-1]['content']+mess}
        self.send_list = self.definition + self.system_list + self.chat_list

    def list_del(self, role, index):
        if role == "user":
            self.chat_list.pop(index)
        elif role == "system":
            self.system_list.pop(index)
