from database import punto_interesse_DAO
from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO
from model import escursione


class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        self._escursione_parco=[]

        self._max_giorni = None
        self._max_budget = None

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        relazioni=EscursioneDAO.get_escursioni_punti_interesse()

        for relazione in relazioni:
            escursione_id=relazione["id_escursione"]
            punto_interesse_id=relazione["id_punto_interesse"]

            if escursione_id in self.escursioni_map and punto_interesse_id in self.punti_interesse_map:
                escursione=self.escursioni_map[escursione_id]
                punto_interesse=self.punti_interesse_map[punto_interesse_id]

                escursione.punti_interesse.add(punto_interesse) #set oggetti
                punto_interesse.escursioni.add(escursione)

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        #lista di escursioni disponibili per parco selezionato
        self._escursione_parco = [escursione for escursione in self.escursioni_map.values()
                                  if id_parco == escursione.id_parco]

        self._max_giorni = max_giorni
        self._max_budget = max_budget

        self._ricorsione(start_index=0,
                         pacchetto_parziale=[],
                         durata_corrente=0,
                         costo_corrente=0,
                         valore_corrente=0,
                         punti_usati=set())

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        #aggiornamento soluzione ottima
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()
            self._costo = costo_corrente

        #condizione per terminare
        if start_index >= len(self._escursione_parco) or \
                (self._max_giorni is not None and durata_corrente >= self._max_giorni) or \
                (self._max_budget is not None and costo_corrente >= self._max_budget):
            return

        #nuove soluzioni
        for i in range(start_index, len(self._escursione_parco)):
            escursione = self._escursione_parco[i]

            #controllo vincoli
            vincoli=self._controllo_vincoli(escursione, punti_usati, durata_corrente, costo_corrente)

            if vincoli is not None:
                nuova_durata, nuovo_costo = vincoli

                #aggiungi escursione
                pacchetto_parziale.append(escursione)
                punti_usati.update(escursione.punti_interesse)

                nuovo_valore = sum(p.voto_visitatori for p in escursione.punti_interesse) + valore_corrente

                self._ricorsione(start_index= i + 1,
                                 pacchetto_parziale=pacchetto_parziale,
                                 durata_corrente=nuova_durata,
                                 costo_corrente=nuovo_costo,
                                 valore_corrente=nuovo_valore,
                                 punti_usati=punti_usati)

                #backtracking
                pacchetto_parziale.pop()
                punti_usati.difference_update(escursione.punti_interesse)

    def _controllo_vincoli(self, escursione, punti_usati, durata_corrente, costo_corrente):

        #punti interesse duplicati
        for punto_interesse in escursione.punti_interesse:
            if punto_interesse in punti_usati:
                return None


        nuova_durata = escursione.durata_giorni + durata_corrente
        nuovo_costo= escursione.costo + costo_corrente

        if self._max_giorni is not None and nuova_durata > self._max_giorni:
            return None

        if self._max_budget is not None and nuovo_costo > self._max_budget:
            return None

        return nuova_durata, nuovo_costo








