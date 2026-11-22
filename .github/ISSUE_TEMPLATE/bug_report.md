---
name: Bug report
about: Something does not work as described
labels: bug
---

**What happened?**

**What did you expect?**

**Environment**
- Home Assistant version:
- Integration version:
- Bluetooth adapter or ESPHome proxy:
- Desk model / controller (e.g. IKEA IDÅSEN, Linak DPG1C):

**Debug log**

Enable debug logging, press a button of the desk entity, and paste the lines containing `custom_components.linak_desk`:

```yaml
logger:
  logs:
    custom_components.linak_desk: debug
```
