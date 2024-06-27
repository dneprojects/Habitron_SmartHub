# Smart Center - Die Systemzentrale und Schnittstelle zum Habitron-Netzwerk

## Einleitung
Das Habitron Smart Center bietet eine vorinstallierte Gesamtlösung zur Kombination eines Habitron Systems mit Home Assistant, einer Plattform zur Integration von smarten Komponenten verschiedener Hersteller zu einer übergreifenden und flexibel erweiterbaren Hausautomatisierung. 
Das Smart Center als Gerät führt gleichzeitig vier Programmteile aus:
### 1. Smart Hub
Der Smart Hub fungiert als Gateway zwischen dem hausinternen Netzwerk (Ethernet oder WLAN) und dem Habitron-Router, der über eine serielle Schnittstelle extern angebunden ist. Der Router wiederum ist mit den installierten Habitron-Modulen, wie Raum-Controllern und Ein- und Ausgangsmodulen, vernetzt. Smart Hub realisiert somit den Zugang in die Habitron-Systemwelt.
Das Software-Modul Smart Hub ist als add-on für Home Assistant verfügbar und mit diesem vorinstalliert. Es benötigt keine Konfiguration. Im Smart Hub add-on ist auch der Smart Configurator enthalten, auch wenn dieser ein eigenständiges Modul darstellt.
### 2. Smart Configurator
Das Smart Center stellt eine Konfigurationsoberfläche bereit, den Smart Configurator. Über diesen lässt sich das Habitron-System mit seinen gesamten Einstellungen konfigurieren. Für die Module können Namen vergeben werden, wie auch für die Ein- und Ausgänge. Auch grundsätzliche Einstellungen, wie die Konfiguration von Eingängen für Taster oder Schalter oder die Bündelung von Ausgängen zur Rollladenansteuerung werden hier vorgenommen. Darüber hinaus werden hier Befehle, Merker und Zähler angelegt und verwaltet, wie auch die Automatisierungen, die direkt auf dem Habitron-System ausgeführt werden sollen.
Die Bedienung des Smart Configurator ist nur für Administratoren vorgesehen.
### 3. Home Assistant
Home Assistant ist auf dem Smart Center Gerät vorinstalliert und wird mit einigen sinnvollen Voreinstellungen ausgeliefert. Für die Anpassung an das eigene Haus mit den dortigen weiteren Komponenten, wie etwa Kameras, Multimediasysteme, etc., lassen sich weitere Integrationen jederzeit nachträglich installieren. Eine der installierten Integrationen ist die für das Habitron-System.
Die Bedienung des gesamten Smart Home erfolgt über die Home Assistant Bedienoberfläche, die eine nahtlose, integrierte Benutzererfahrung über die Systeme der unterschiedlichen Hersteller hinweg ermöglicht. Neben der übergreifenden Bedienbarkeit lassen sich in Home Assistant auch Automati-sierungen anlegen, die innerhalb, aber auch zwischen den verschiedenen Herstellersystemen wirken.
### 4. Habitron-Integration
Als Basis für das Zusammenspiel mit dem Habitron Smart Hub ist die Habitron-Integration vorinstalliert. Dieses Software-Modul stellt die Schnittstelle des Smart Center zu Home Assistant bereit. Die Integration fragt das Habitron-System nach vorhandenen Controllern und Modulen ab und fügt die entsprechenden Funktionalitäten als Home Assistant Entitäten ein, z.B. Rollladen, Licht, Schalter, Sensoren und mehr.

In den folgenden Abschnitten wird die Inbetriebnahme, die Konfiguration, die grundsätzliche Bedienung und das Anlegen von Automatisierungen beschrieben. Zuvor sollen jedoch noch einige Grundbegriffe erklärt werden, die von Home Assistant verwendet werden.

## Grundbegriffe von Home Assistant
Vorab sollen noch ein paar Grundbegriffe erklärt werden, die in dieser Beschreibung und den Dialogen bei Home Assistant immer wieder vorkommen.

### Entitäten
Die grundlegende Einheit in Home Assistant ist die Entität. Eine Entität hat einen bestimmten Typ, z.B. ein Licht oder ein Schalter, ein Sensor oder ein Rollladen. Jede Entität hat je nach Typ unterschiedliche Eigenschaften und Möglichkeiten. So kann ein Licht dimmbar oder nur schaltbar sein, aber auch eine Farbe oder eine Farbtemperatur des Weißtons annehmen. Eine Klima-Entität kann heizen und/oder kühlen.
Entitäten und ihre Eigenschaften werden beim Hochfahren von Home Assistant automatisch erkannt. Für das Habitron-System übernimmt dies die Habitron-Integration auf Basis der Einstellungen, die über den Smart Configurator zuvor vorgenommen wurden. 

### Geräte
Geräte sind in Home Assistant Einheiten, die typischerweise mehrere Entitäten mitbringen. Ein Habitron Raumcontroller hat, je nach Konfiguration, 40 – 60 Entitäten, nämlich alle seine Ein- und Ausgänge, Sensoren, Merker, Befehle, etc.

### Integrationen
Die unterschiedlichen Geräte und Entitäten werden über Software-Module, die Integrationen, zur Verfügung gestellt. Home Assistant beinhaltet eine Reihe grundsätzlicher Integrationen, z.B. zur Systemüberwachung. Weitere Integrationen dienen der Einbindung bestimmter Geräteklassen, z.B. Leuchten, die über die Funktechnologie ZIGBEE angesteuert werden. Ein weiteres Beispiel sind Integrationen für das Streamen von Audio- oder Video-Daten, oder zur Einbindung von Überwachungskameras.

Eine große Anzahl von Integrationen ist bereits vorinstalliert, so dass Home Assistant diese Geräte automatisch im Netzwerk detektieren kann, andere können bei Bedarf nachträglich installiert werden.

### Bereiche
Home Assistant ermöglicht es, Geräte oder einzelne Entitäten einem Bereich zuzuordnen, typischerweise einem Raum. Das erlaubt es nicht nur, Bedienelemente besser zu gruppieren, sondern auch Kommandos zum Ausschalten des Lichts in einem Raum mit einem Befehl vorzunehmen. Anfangs sollte jedes Gerät einem Raum sinnvoll zugeordnet werden. Wenn einzelne Entitäten eines Controllers, z.B. ein Ausgang eines Moduls, für einen anderen Raum relevant sein sollten, kann man das später verfeinern. Bereiche bieten zusätzlich die Möglichkeit, einer Etage zugeordnet zu werden, um etwa das Licht im gesamten Obergeschoss zu schalten.

### Labels
Labels sind eine weitere Methode, um Entitäten zu gruppieren. Eine Entität kann nur einem Bereich zugeordnet werden, aber mehreren Labels. Denkbar wären Kategorien, wie „Energie“, „Wasser“ oder speziell bei Habitron-Ein- oder Ausgängen „24V“. Mit Hilfe der Label können einzelne Entitäten, wie bei den Bereichen, zusammengefasst werden, um Regeln zu vereinfachen oder in Listen gruppieren und sortieren zu können. Anders als Bereiche, deren Definition und Vergabe von Anfang an vorgenommen werden sollte, können Labels später zur Verfeinerung hinzugefügt werden.

### Zonen
Zonen sind geografische Bereiche, die genutzt werden sollen, um Automatisierungen auszulösen. Zu den Grundeinstellungen gehört die „Home“-Zone um die eigene Adresse, bei dessen Verlassen oder Eintritt sich z.B. eine Verriegelung oder eine Temperaturabsenkung steuern lässt. Zonen werden über eine Adresse oder einen Punkt auf der Karte definiert und haben einen Radius um diesen Punkt.

### Automatisierungen
Automatisierungen verknüpfen die verschiedenen Entitäten miteinander und sorgen so für smarte Funktionen. Die einfachste Form der Automatisierung ist das Ereignis eines Tastendrucks mit einer Ausgangsänderung zu verbinden. In Home Assistant lassen sich Regeln sehr flexibel und elegant definieren, indem verschiedene Auslöser mit verschiedenen Bedingungen verknüpft verschiedene Aktionen auslösen lassen. So kann eine einzige Regel in Home Assistant einen komplexeren Zusammenhang definieren und selbstverständlich Entitäten unterschiedlicher Hersteller miteinander verknüpfen.

Automatisierungen lassen sich sowohl in Home Assistant definieren, als auch in bestimmten Systemen, wie bei Habitron, lokal. Dies kann zur Unsicherheit führen, dass unklar ist, ob eine bestimmte Automatisierung im Habitron-System oder bei Home Assistant definiert wurde. Daher empfiehlt es sich, ein paar grundsätzliche Kriterien zu berücksichtigen:

-	Eine Automatisierung, die verschiedene Systeme verknüpft, muss in Home Assistant angelegt werden.
-	Eine Automatisierung, die komplexere Bedingungen enthält oder verschiedene Entitäten gleich verknüpft, sollte bei Home Assistant definiert werden, weil im Habitron-System dafür zusätzliche Definitionen nötig werden, wie z.B. Sammelbefehle.
-	Eine Richtschnur kann sein, nur solche Automatisierungen im Habitron-System anzulegen, die lokal auf einem Controller ausgeführt werden, z.B. Licht- oder Rollladenaktionen, die über lokal am Controller angeschlossenen Tastern ausgelöst werden. Diese Aktionen bleiben selbst dann verfügbar, wenn eine Störung im System vorliegen sollte.

### Szenen
Home Assistant bietet eine besondere Form der Automatisierung, die Szene. Anders als bei einer Automatisierung muss eine Szene nicht programmiert werden, sondern sie wird konfiguriert, indem man die Entitäten, die Teil der Szene sein sollten, auswählt und deren aktuellen Zustand übernimmt. Dieser Zustand besteht nicht nur aus dem Schaltzustand, sondern z.B. auch der Farbe eines Lichts, der Position eines Rollladens oder einer Solltemperatur des Raumes.

Man schaltet also das Licht in der gewünschten Helligkeit und Farbe ein oder aus, bringt die alle weiteren Entitäten, die Teil der Szene sein sollen, in den gewünschten Zustand und definiert dann die entsprechende Szene. Szenen können selbst wieder Teil einer Automatisierung sein, um z.B. auf diese Weise ausgelöst zu werden.

### Skripte und Blaupausen
Mit Hilfe von Skripten lassen sich noch komplexere Automatisierungen programmieren. Während eine „normale“ Automatisierung mit Hilfe der Benutzeroberfläche zusammengestellt wird, muss ein Skript programmiert werden.
Eine Blaupause ist eine Vorlage für mehrere Automatisierungen, die immer gleichartig funktionieren. Ein Beispiel, das Home Assistant mitliefert, ist eine Lichtsteuerung durch einen Bewegungssensor: Man passt nur noch die Entitäten für den Sensor und das Licht, sowie die Einschaltdauer an.

### Dashboards
Dashboards sind die Bedienfelder, über die die eigentliche Bedienung des Smart Home erfolgt. Wenn alle Geräte und Integrationen eingerichtet sind, lassen sich hier sehr frei unterschiedliche Visualisierungs- und Bedienkonzepte umsetzen. Es können mehrere Dashboards angelegt werden, die auch je Benutzer unterschiedlich freigegeben werden.

Die „Übersicht“, das Standard-Dashboard, zeigt automatisch alle im System vorhandenen Entitäten, gruppiert auf unterschiedlichen Kacheln je Bereich. Ein „Energie“-Dashboard kann die Energieflüsse visualisieren, sofern Sensoren für die Stromflüsse vorhanden sind.

## Inbetriebnahme

### Anschluss der Hardware

Das Smart Center ist in einem Gehäuse verbaut, das die Montage im Sicherungskasten auf einer Hutschiene vorsieht. Das mitgelieferte Kabel muss mit dem seriellen Port des Smart Center und dem Router verbunden werden. Für die Inbetriebnahme muss das Smart Center über ein Kabel mit dem Ethernet verbunden werden. Später kann auf Wunsch auch eine WLAN-Verbindung konfiguriert werden und das Kabel wieder entfernt werden.

Wenn die serielle und die Netzwerkverbindung herstellt sind, kann die Spannungsversorgung eingesteckt werden und das System bootet. Nach etwa einer Minute kann lässt sich die Oberfläche von Home Assistant über den Browser erreichen.

Dazu gibt man in die Adresszeile ein: „smartcenter:8123“

Es erscheint ein Anmeldedialog, in dem als Benutzername „habitron_admin“ und als Passwort „habitron“ eingegeben werden muss. Das Passwort sollte, zusammen mit einigen weiteren Einstellungen, gleich geändert werden.

### Grundeinstellungen von Home Assistant
Bevor man mit der Bedienung beginnt, sollten einige Einstellungen vorab vorgenommen werden, die aufeinander aufbauen. Auch wenn sich alle Einstellungen auch nachträglich anpassen lassen, empfiehlt es sich, diese Vorgehensweise in der beschriebenen Reihenfolge einzuhalten.

Die Einstellungen von Home Assistant erreicht man, indem an der linken Seite der Weboberfläche das Zahnradsymbol geklickt wird.

#### Benutzerverwaltung
Als erstes sollte für jeden Bediener des Systems eine Person angelegt werden. Dazu gibt es im Bereich der Einstellungen den Bereich der „Personen“. Rechts unten auf der Personen-Seite lässt sich über den schwebenden Button „+ PERSON HINZUFÜGEN“ eine neue Person anlegen. 

Home Assistant unterscheidet zwischen Personen und Benutzern. Einer Person kann über ein Gerät, typischerweise ein Mobiltelefon, ein Anwesenheitsstatus zugeordnet werden, der wiederum als Auslöser einer Automatisierung genutzt werden kann. Ein Benutzer kann sich am System anmelden und dieses bedienen. Dazu wird der Schiebeschalter „Erlaube dieser Person, sich einzuloggen“ aktiviert. In der Benutzerverwaltung wird nun ein Passwort vergeben und die Zugehörigkeit zur Administratorengruppe festgelegt.

Für den Einstieg sollte man sich selbst als Person und Benutzer mit Administratorrechten anlegen. Der Dialog wird unten rechts mit „AKTUALISIEREN“ abgeschlossen. Nach dem Abmelden, dazu klickt man an der linken Seite auf das Personensymbol, betätigt das rote „ABMELDEN“ und bestätigt die Rückfrage, kann man sich unter dem soeben angelegten Benutzernamen neu anmelden. Es ist sinnvoll, über das Personensymbol links unten bei den Benutzereinstellungen den „Erweiterten Modus“ einzuschalten, da sonst einige Optionen nicht freigeschaltet sind.

Nachdem der Anmeldung unter der neuen Identität können weitere Personen angelegt werden. Die Administratorbefugnis erlaubt den Zugriff auf die gesamte Home Assistant Funktionalität und sollte daher nicht grundsätzlich für alle Benutzer vergeben werden. Der Benutzer „habitron_admin“ kann nur über eine Neuinstallation gelöscht werden, da dieser der Besitzer der Home Assistant Instanz ist.

#### Bereiche, Etagen und Zonen
Jedem Gerät (und bei Bedarf auch einer einzelnen Entität) kann ein Bereich zugeordnet werden. Daher sollten diese Bereiche vor der Detektion von Geräten bereits angelegt werden. Für ein ansprechendes Erscheinungsbild der Home Assistant Oberfläche empfiehlt es sich, Fotos von den Bereichen zu machen und diese hier hochzuladen. Dieser Schritt kann aber auch später jederzeit nachgeholt werden.

Zum Anlegen der Bereiche wählt man links in der Seitenleiste die „Einstellungen“ und dann den Punkt „Bereiche, Labels & Zonen“. Jetzt kann man für jeden Raum einen „Bereich“ anlegen und jeden Bereich einer Etage zuordnen. Etagen besitzen je nach Stockwerk ein Symbol (Icon), das vorgeschlagen wird. Den Bereichen kann man selbst ein gewünschtes Symbol zuordnen, indem man entweder in der Liste sucht, oder in das Feld tippt, z.B. „bed“ schränkt die Auswahl auf alle Symbole ein, die diese drei Buchstaben im Namen enthalten.

### Grundeinstellungen im Habitron-System

In der Seitenleiste befindet sich ein Habitron-Symbol mit der Beschriftung „Habitron Smart Hub“. Über diesen Eintrag erreicht man jederzeit den Smart Configurator. Dort sollten, bevor die Detektion der Module erfolgt, die notwendigen Grundeinstellungen vorgenommen werden.

Grundsätzlich ist zu beachten, dass nicht benannte Ein- oder Ausgänge, wie auch andere Elemente ohne Namen, von der Habitron-Integration für Home Assistant als nicht existent behandelt werden. Es wird davon ausgegangen, dass alle relevanten Entitäten einen Namen besitzen. Daher ist dieser Konfigurationsvorgang vor Beginn der Detektion wichtig. Zwar sind auch nachträgliche Änderungen möglich, aber dazu muss die Integration neu geladen werden und gelöschte Einträge führen zu verwaisten Entitäten in Home Assistant.

Für die genauere Informationen ist das Kapitel „Bedienung des Smart Configurator" zu beachten.

Es wird dringend geraten, die Einstellungen des Routers und aller Module einmal durchzugehen:
-	Alle benötigten Taster, Schalter und Ausgänge müssen mit Namen versehen sein.
-	Obligatorisch ist ferner bei den Eingängen die Einstellung, ob es sich um einen Taster oder einen Schalter handelt.
-	Bei den Ausgängen sind die Rollladenbeschaltungen und deren Polarität zu wählen. Ein Textfeld je Rollladen erlaubt die Einstellung der Zeit zum Öffnen/Schließen, um eine Positionsansteuerung zu ermöglichen. 
-	Jalousien lassen sich von Rollladen nur anhand einer gesetzten zweiten Verstellzeit unterscheiden, dieses Feld muss bei Rollladen eine Null enthalten.

### Erfassung des Habitron-Systems in Home Assistant

Nach diesen Grundeinstellungen in Home Assistant und im Habitron-System, kann nun die Integration gestartet werden. Dazu wird unter „Einstellungen“ / „Geräte & Dienste“ im Bereich der konfigurierten Integrationen (unten) die Kachel „Habitron“ gewählt. Auf der nun erscheinenden Seite gibt es rechts ein Menu mit drei Punkten, aus dem „Neu laden“ geklickt wird. 

Die Habitron-Integration wird nun neu gestartet und fragt über den Smart Hub das System nach seinen Modulen und Einstellungen. Dieser Schritt ist übrigens immer dann erneut notwendig, wenn Veränderungen an der Konfiguration des Habitron-Systems vorgenommen werden.

Die gefundenen Geräte mit ihren Ein-, Ausgängen und Sensoren werden dann als Geräte und Entitäten angelegt. Nach diesem Vorgang erscheint ein Fenster, in dem alle neu gefundenen Geräte aufgeführt sind. Diese können in diesem Schritt jeweils einem zuvor definierten Bereich zugeordnet werden. Ansonsten lassen sich auch in diesem Schritt Bereiche neu anlegen.

Danach ist die Einrichtung abgeschlossen. Alle Geräte und Entitäten erscheinen auf einem Standard-Dashboard, das in der Seitenleiste ganz oben mit den Namen „Übersicht“ zu finden ist. Dort befinden sich Kacheln für jeden Bereich mit einer Liste aller jeweiligen Entitäten.

## Bedienung des Smart Configurator

Der Smart Configurator erlaubt die vollständige Konfiguration des Habitron-Systems über eine Web-Bedienoberfläche. Zugänglich ist dieser nur für Administratoren von Home Assistant, um „normalen“ Nutzern nicht die Möglichkeit zu geben, kritische Änderungen vorzunehmen. Die Daten sind nicht im Configurator gespeichert, sondern werden über den Smart Hub aus dem System ausgelesen und dargestellt. Beim Speichern von Änderungen werden diese direkt zurück ins System gespeichert und entweder im Router oder in den Modulen abgelegt.

### Einstellungen für den Router

Auf der linken Menuleiste lassen sich die Übersichtsseiten für den Hub, den Router und die Module anwählen. Auf der Übersicht für den Router kann in den Einstellungsmodus gewechselt oder Konfigurationsdateien in den Router hoch- oder aus diesem heruntergeladen werden. Jeder der Schritte kann grundsätzlich wieder abgebrochen werden, bevor etwas Unerwünschtes in der Anlage passiert.

Die Einstellungen erfolgen über mehrere Seiten, die mit den Tasten „weiter“ oder „zurück“ gewechselt werden können. Erst mit dem „Speichern“ Button erfolgt die Übernahme ins System. Dann werden die Einstellungen im Router gespeichert. Ein Abbruch macht alle Änderungen, die auf den Einstellungsseiten ohne zu speichern gemacht wurden, rückgängig.

Auf der ersten Seite erhält der Router einen Namen. Außerdem lassen sich die beiden benutzerdefinierten Modi, die zusätzlich zu den Standard-Modi, wie „Anwesend“, „Abwesend“, „Schlafen“ und „Urlaub“ zur Verfügung stehen, mit einem aussagekräftigen Namen versehen. Die folgenden beiden Seiten dienen der Einstellung der Tag-/Nachtumschaltung.

Auf der folgenden Seite werden Gruppennamen vergeben. Die Gruppen dienen dem Zweck, die Modi sowie die Zustände „Tag“/ „Nacht“ und „Alarm“ in Bereichen unabhängig voneinander steuern zu können. Während die Modi, z.B. „Anwesend“ in den Gruppen immer unabhängig voneinander sind, können Tag/Nacht und Alarm über die Gruppe 0 übergreifend verwendet werden. Wenn also unabhängige Zustände erwünscht sind, müssen hier Gruppen angelegt werden.

Dazu wird im unteren Feld eine Zahl eingegeben oder die Pfeiltasten am rechten Rand der Textbox verändert. Es erfolgt eine Überprüfung auf den Wertebereich und bereits vergebene Zahlen dürfen nicht eingegeben werden, in diesem Fall wird der nächste freie Zahlenwert übernommen. Neu angelegte Gruppen erhalten einen allgemeinen Namen, der umbenannt werden sollte. Über die Auswahlkästchen rechts lassen sich existierende Einträge wählen und daraufhin entfernen.

Seite drei zeigt alle definierten globalen Merker. Merker sind systeminterne Variablen in der Habitron-Anlage, die für Automatisierungen genutzt werden können. 16 Merker sind im Router abgespeichert und können in allen Modulen verwendet werden, weitere 16 sind lokal in den Modulen hinterlegt, werden in deren Einstellungen verwaltet und lassen sich auch nur in deren Automatisierungen nutzen. Die Bedienung erfolgt bei allen Einstellungen in gleicher Weise: Mit einer neuen Nummer wird ein Element angelegt, das danach umbenannt werden kann. Vorhandene Einträge können selektiert und entfernt werden.

Die letzte Seite erlaubt die Verwaltung von bis zu 255 Sammelbefehlen in derselben Weise.

Wenn alle Einstellungen erfolgt sind, bitte das Speichern nicht vergessen!

### Einstellungen für die Module

Nach der Auswahl des Menupunkts „Module“ wird eine Übersicht aller im System vorhandenen Module dargestellt. Jedes Modul bietet auf seiner Übersichtsseite Informationen zur Adresse, den Routerkanal, über den das Modul angebunden ist, und einer Seriennummer sowie dem Softwarestand der Firmware. Bei Modulen, die Aktoren steuern, ist neben den Buttons für die Einstellungen und die Konfigurationsdatei auch ein dritter verfügbar, um die Automatisierungen zur verwalten. Die Einstellungsseiten unterscheiden sich je nach Typ des Moduls. Hier ist exemplarisch der Raumcontroller beschrieben, die anderen Module bieten weniger Konfigurationsoptionen.

Die erste Seite mit den Grundeinstellungen enthält den Modulnamen und dessen Gruppenzugehörigkeit. Es werden grundsätzlich nur Gruppen angeboten, die mit einem Namen versehen wurden, bei anderen, unbenannten Gruppen wird davon ausgegangen, dass diese nicht relevant sind.

Raumcontroller bieten zusätzlich Einstellungen für das Display, Tastenzeiten, das Dimmen, die Klimatisierung und die Priorität der Spannungsversorgung. 

Seite zwei ermöglicht die Benennung der acht Modultasten. Auch hier gilt, nicht benannte Tasten erscheinen nicht in Home Assistant als Entitäten. Nachfolgend können die acht roten Signal-LEDs mit Namen versehen werden. Die Einstellungen der Eingänge umfassen neben die Namen die Umschaltung zwischen Taster und Schalter. Beim Input-Modul mit 24V-Eingängen lassen sich zusätzlich sechs der Eingänge zu Analogeingängen umkonfigurieren. Auf der Seite der Ausgänge sind ebenfalls Namen für alle verwendeten Ausgänge zu vergeben.

Bei den ersten fünf Ausgangspaaren ist zusätzlich der Schalter für eine Rollladenverschaltung zu setzen, die sich auf die Folgeseite auswirkt. Dort sind für die als Rollladen konfigurierten Paare Einstellungen zu finden. Der Name wird von der vorherigen Seite übernommen, allerdings werden Bezeichnungen wie „auf“, „ab“, „up“, „down“ aus dem Namen entfernt und je nach hier definierter Polarität für die einzelnen Ausgänge des Paares angepasst. Je Rollladen sind zwei Textfelder vorhanden, um die Zeiten für die Verstellung eintragen zu können. Das erste Feld beschreibt das Öffnen/Schließen des Rollladens. Ist im zweiten Feld ein Wert größer als Null eingetragen, wird der Rollladen als Jalousie erkannt, die zweite Zeit beschreibt dann die Zeit für das Umlegen der Lamellen.

Auf der nächsten Seite lassen sich Zähler anlegen. Wie grundsätzlich wird zuerst eine Nummer vergeben, dann erscheint in diesem Fall ein Popup-Fenster mit der Abfrage, wie viele Zählerwerte zulässig sind (wenn der obere Wert beim Hochzählen überschritten wird, geht es zurück auf die Eins). Danach können Logikfunktionen für das Modul verwaltet werden. Hier wird beim Neuanlegen über ein popup abgefragt, um welche Logikfunktion es sich handeln (AND, NAND, OR, NOR) und wie viele Eingänge die Funktion haben soll.

Die Folgeseiten erlauben die Verwaltung von lokalen Merkern, Direktbefehlen und Visualisierungsbefehlen, sowie Meldungstexten.

Auch bei den Einstellungen für die Module am Ende bitte das Speichern nicht vergessen. Alle Einstellungen, die bis dahin gemacht werden, sind nur vorläufig, d.h. mit „Abbruch“ kann man jederzeit Eingaben wieder verwerfen. „Speichern“ startet einen Upload der Einstellungen ins entsprechende Modul. 

### Automatisierungen

Auf der Übersichtsseite jedes Moduls, das Aktionen ausführen kann, befindet sich unten ein Button „Automatisierungen“, über den sich eine Liste der im Modul gespeicherten Automatisierungen anzeigen lässt. Auf einer ersten Seite werden alle lokalen Verknüpfungen angezeigt, die Auslöser auf dem entsprechenden Modul mit Aktionen desselben Moduls verbinden. Über den „weiter“-Button lassen sich die Automatisierungen anzeigen, die von anderen Modulen ausgelöst werden. Die Listen lassen sich nach Auslösern, Bedingungen oder Aktionen sortieren, um gleichartige Regeln schneller auffinden zu können.

Die Bedienung erfolgt auf beiden Seiten identisch. Eine der Automatisierungsregeln ist immer ausgewählt. Diese kann entweder gelöscht, geändert oder als Vorlage für eine neue Regel genutzt werden. Beim Löschen erscheint ein Popup mit einer Rückfrage, die eine Freigabe oder das Abbrechen des Löschvorgangs ermöglicht. 

Beim Neuanlegen oder Ändern erscheint ein neues Fenster mit der Übersicht des entsprechenden Befehls. Durch die vorherige Auswahl eines Befehls sind auch beim Anlegen bereit alle Felder befüllt, können aber beliebig geändert werden. Die Eingabe ist in drei Bereiche gegliedert: Auslöser, Bedingung und Aktion. Die Konfiguration erfolgt mit Ausnahme einiger Zahlenwerte komplett über Auswahlboxes, bei denen nur gültige Auswahlen möglich sind. Diese richten sich nach dem Modul und dessen Konfiguration. 

Wenn etwa ein Modul keine Taster hat oder alle Eingänge als Schalter konfiguriert sein sollte, kann als Auslöser kein Tasterereignis gewählt werden. Wenn ein Tasterereignis als Auslöser gewählt wurde, muss in der zweiten Box aus der Liste einer der als Taster konfigurierten Eingänge gewählt werden. Dann ist noch festzulegen, ob ein kurzer oder langer Tastendruck die Regel auslösen soll. In ähnlicher Weise erfolgt die Konfiguration der anderen Auslöser, einer Bedingung oder einer Aktion. Einen Unterschied gibt es beim Neuanlegen einer externen Automatisierung: Vor dem Öffnen der Einstellungsseite erscheint ein Popup mit der Abfrage nach dem auslösenden Modul.

Die Einstellungen lassen sich folgenlos vornehmen. Wenn eine Automatisierung definiert ist, wird die Seite mit „OK“ geschlossen, ein Abbruch ist ebenfalls möglich. Die neue oder geänderte Automatisierung erscheint in der Liste und ist dort für den nächsten Schritt selektiert. So können mehrere, ähnliche Automatisierungen zügig eingegeben werden, wenn sich diese nur in wenigen Auswahlpunkten unterscheiden. Zum Abschließen der gesamten Programmierung gilt dasselbe wie für die Konfiguration. Es lassen sich beliebig viele Regeln anlegen, ändern und löschen, solange nicht auf „Speichern“ gedrückt wird, bleiben diese Änderungen temporär und können mit einem Abbruch jederzeit verworfen werden. „Speichern“ überträgt diese als neue Konfiguration ins entsprechende Modul.

### Datensicherung

Auf jeder Übersichtsseite eines Moduls oder des Routers kann ein Dialog für die Konfigurationsdatei geöffnet werden. Über einen Download wird die vollständige Konfiguration des entsprechenden Moduls unter dem angegebenen Dateinamen in den Download-Ordner des Endgerätes gespeichert. Umgekehrt kann mit Hilfe des Auswahlfensters eine Konfigurationsdatei ausgewählt werden, die im Modul gespeichert wird. Dabei wird zuvor überprüft, ob die in der Datei abgelegte Moduladresse und der Modultyp mit dem aktuellen Modul übereinstimmt.

Über die Hub-Seite kann auch die Konfiguration des gesamten Systems in einer Datei heruntergeladen werden (Backup), bzw. wieder in alle Module rückgespielt werden (Restore).

### Updates

Grundsätzlich bietet Smart Center eine automatische Versorgung mit Updates, auch für die Firmware von Modulen und Router. Der aktuelle Stand aller Firmware-Dateien wird mit jeder neuen Version des Smart Hub Add-ons ausgerollt. Wenn ein Modul oder der Router einen davon abweichenden Firmwarestand aufweisen sollte, erfolgt über Home Assistant eine Information, über die dann auch der Update-Vorgang angestoßen werden kann. Dies ist möglich, ohne den Smart Configurator zu benutzen.

Zusätzlich kann von der Übersichtsseite des Hubs ein Update der Router- oder Modulfirmware auf einen beliebigen Stand vorgenommen werden. Dazu ist zunächst auf dem lokalen Gerät eine Firmwaredatei auszuwählen, die dann auf den Hub geladen wird. Danach ist immer noch ein Abbruch möglich. Bei Modulen findet im Anschluss ein Vergleich mit den im System vorhandenen Modulen statt und es wird eine Übersicht aller Module des zur Firmware kompatiblen Typs dargestellt. Wenn die Firmware neuer ist als der Firmwarestand eines Moduls, wird dieses selektiert dargestellt. Manuell lassen sich jetzt Module anwählen oder abwählen, um gezielt nur bestimmte Module mit der veränderten Firmware zu flashen. Über eine manuelle Selektion kann auch ein älterer Firmwarestand geflasht werden.

Wenn der Button „Flashen“ gedrückt wurde, ist der Vorgang nicht mehr abzubrechen. In den Kacheln der Module wird ein Status eingeblendet. Sollte dieser Status für einige Zeit lang unverändert bleiben, kann dies am Smart Center liegen, das in der Zeit einen anderen Prozess ausführt. Dies hat jedoch keine Auswirkung auf den Update-Prozess, der vom Router ohne Zutun des Smart Center durchgeführt wird. Für die Zeit des Flash-Vorgangs ist der Smart Hub für externe Kommandos gesperrt.

## Lizenzen

Über die Einstiegsseite, die auch über einen Klick auf den Schriftzug „Smart Configurator“ oben rechts erreichbar ist, kann eine Tabelle angezeigt werden, die alle von Smart Hub, Smart Center und Home Assistant verwendeten Softwarepakete und deren Open Source Lizenzen auflistet. Diese Tabelle wird automatisiert aufbereitet und dieser Vorgang dauert einige Sekunden.
