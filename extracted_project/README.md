# Драйвер
Драйвер основан на ядреном модуле для CentOS и Ubuntu. Рекомендуется использовать ядро версии 5.12 и выше.

# Инструкция
Убедитесь, что опция vt-d включена в BIOS.
Выполните перекомпиляцию (remake), затем выполните modprobe ptp_ocp.

## Результат
```
$ ls -g /sys/class/timecard/ocp0/
total 0
-r--r--r--. 1 root 4096 Sep  8 18:20 available_clock_sources
-r--r--r--. 1 root 4096 Sep  8 18:20 available_sma_inputs
-r--r--r--. 1 root 4096 Sep  8 18:20 available_sma_outputs
-rw-r--r--. 1 root 4096 Sep  8 18:20 clock_source
lrwxrwxrwx. 1 root    0 Sep  8 18:20 device -> ../../../0000:02:00.0
-rw-r--r--. 1 root 4096 Sep  8 18:20 external_pps_cable_delay
-r--r--r--. 1 root 4096 Sep  8 18:20 gnss_sync
-rw-r--r--. 1 root 4096 Sep  8 18:20 internal_pps_cable_delay
-rw-r--r--. 1 root 4096 Sep  8 18:20 irig_b_mode
-rw-r--r--. 1 root 4096 Sep  8 18:20 pci_delay
drwxr-xr-x. 2 root    0 Sep  8 18:20 power
lrwxrwxrwx. 1 root    0 Sep  8 18:20 ptp -> ../../ptp/ptp4
-r--r--r--. 1 root 4096 Sep  8 18:20 serialnum
-rw-r--r--. 1 root 4096 Sep  8 18:20 sma1_in
-rw-r--r--. 1 root 4096 Sep  8 18:20 sma2_in
-rw-r--r--. 1 root 4096 Sep  8 21:04 sma3_out
-rw-r--r--. 1 root 4096 Sep  8 21:04 sma4_out
lrwxrwxrwx. 1 root    0 Sep  8 18:20 subsystem -> ../../../../../../class/timecard
lrwxrwxrwx. 1 root    0 Sep  8 18:20 ttyGNSS -> ../../tty/ttyS5
lrwxrwxrwx. 1 root    0 Sep  8 18:20 ttyMAC -> ../../tty/ttyS6
lrwxrwxrwx. 1 root    0 Sep  8 18:20 ttyNMEA -> ../../tty/ttyS7
-rw-r--r--. 1 root 4096 Sep  8 18:20 uevent
-rw-r--r--. 1 root 4096 Sep  8 18:20 utc_tai_offset
```

Основной каталог ресурсов доступен по адресу /sys/class/timecard/ocpN, предоставляя ссылки на различные ресурсы TimeCard. Ссылки на устройства легко использовать в сценариях:

```
  tty=$(basename $(readlink /sys/class/timecard/ocp0/ttyGNSS))
  ptp=$(basename $(readlink /sys/class/timecard/ocp0/ptp))

  echo "/dev/$tty"
  echo "/dev/$ptp"
```

После успешной загрузки драйвера появятся:
* PTP POSIX clock, связанный с физическим аппаратным часами (PHC) на Qantum Card  (`/dev/ptp4`) 
* GNSS serial `/dev/ttyS5` 
* Atomic clock serial `/dev/ttyS6`
* NMEA Master serial `/dev/ttyS7`
* i2c (`/dev/i2c-*`) device

Теперь можно использовать стандартные инструменты linuxptp, такие как phc2sys или ts2phc для копирования, синхронизации, настройки и т.д. 

## Драйвер включен в основное ядро Linux
* Первоначальная примитивная версия ([5.2](https://git.kernel.org/pub/scm/linux/kernel/git/netdev/net-next.git/commit/?id=a7e1abad13f3f0366ee625831fecda2b603cdc17))
* Версия, раскрывающая все устройства ([5.15](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=773bda96492153e11d21eb63ac814669b51fc701)) 