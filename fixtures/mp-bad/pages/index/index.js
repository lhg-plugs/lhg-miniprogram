// 坏用例：埋点 MP-SEC-001 / MP-API-001 / MP-RTE-001 / MP-DATA-001 / MP-HYG-001 / MP-HYG-002 / MP-HYG-003
const appsecret = "wx9f8e7d6c5b4a39281706f5e4d3c2b1a";

Page({
  data: { list: [] },
  onLoad() {
    console.log("调试输出残留");
    wx.request({ url: 'http://api.example.com/list' });
    try {
      this.loadData();
    } catch (e) {}
  },
  loadData() {
    for (var i = 0; i < 10; i++) {
      wx.setStorageSync("key_" + i, i);
    }
    debugger;
  },
  goHome() {
    wx.navigateTo({ url: '/pages/index/index' });
  }
});
