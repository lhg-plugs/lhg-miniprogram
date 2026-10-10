// 好用例：隐私协议处理 + 干净代码
const { request } = require('../../utils/request.js');

wx.onNeedPrivacyAuthorization((resolve) => {
  // 用户点击同意后同步给平台
  resolve({ event: 'agree', buttonId: 'agree-btn' });
});

Page({
  data: { list: [] },
  onLoad() {
    this.loadData();
  },
  async loadData() {
    try {
      const res = await request({ url: 'https://api.example.com/list' });
      this.setData({ list: res.data || [] });
    } catch (err) {
      wx.showToast({ title: '加载失败，请重试', icon: 'none' });
    }
  }
});
