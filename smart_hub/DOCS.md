# Smart Center - Die Systemzentrale und Schnittstelle zum Habitron-Netzwerk

## Einleitung

Smart Center besteht aus zwei Teilen:
1. Smart Hub
2. Home Assistant

Smart Hub fungiert als Gateway zwischen dem hausinternen 
Netzwerk (Ethernet oder WLAN) und dem Habitron-Router, 
der über eine serielle Schnittstelle angebunden ist.

Der Router wiederum ist mit
den installierten Habitron-Modulen vernetzt,
wie Raum-Controllern und Ein- und Ausgangsmodulen.

Smart Hub bietet ebenfalls eine Web-Oberfläche an, den
Smart Configurator, über den sich die Konfiguration der Habitron 
Module vornehmen lässt. So können grundlegende Einstellungen, 
wie Namen der Module oder der Ein- und Ausgänge definiert werden. 
Es lassen sich auch die Automatisierungen anlegen, ändern oder 
löschen, die intern in den Habitron-Modulen gespeichert und 
ausgeführt werden.

Über den Smart Hub besteht auch ein Zugang für Home Assistant, 
das auf demselben Gerät installiert ist. Home Assistant kommuniziert 
intern mit Smart Hub und erkennt über die spezielle Habitron-
Integration, ein umfangreiches Softwarepaket, alle Module und 
deren Konfiguration und Eigenschaften. So lassen sich alle 
Module über Home Assistant und dessen grafische Oberfläche bedienen,
aber auch mit Geräten anderer Hersteller in gemeinsame
Automatisierungen und Szenen einbinden.
