# -*- coding: utf-8 -*-
r"""
gabarits.pyw — Appliquer les gabarits par style, pour DesignCraft.

Lancer DesignCraft avec le canal de controle :
    & "C:\Program Files\ArtCraft\DesignCraft\designcraft.exe" --control 7979
puis ouvrir le document, puis lancer ce script.

Cyril Soler-Bonnet / Editions localement transcendantes.
"""
import json, os, queue, socket, threading, tkinter as tk
from tkinter import ttk, messagebox, simpledialog

PORT_DEFAUT = 7979
FICHIER_PRESETS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "gabarits_presets.json")


# ---------------------------------------------------------------- canal

class Canal:
    def __init__(self, port=PORT_DEFAUT):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=300)
        self.flux = self.sock.makefile("rwb")
        self.n = 0

    def appel(self, methode, params=None):
        self.n += 1
        r = {"id": self.n, "method": methode}
        if params is not None:
            r["params"] = params
        self.flux.write((json.dumps(r) + "\n").encode("utf-8"))
        self.flux.flush()
        ligne = self.flux.readline()
        if not ligne:
            raise RuntimeError("DesignCraft a ferme le canal.")
        rep = json.loads(ligne.decode("utf-8"))
        if not rep.get("ok"):
            raise RuntimeError("%s : %s" % (methode, rep.get("error", rep)))
        return rep.get("result")

    def cmd(self, nom, params=None):
        return self.appel("engine.execute",
                          {"command": nom, "params": params or {}})

    def fermer(self):
        try:
            self.flux.close(); self.sock.close()
        except Exception:
            pass


# ------------------------------------------------------------- analyse

def geometrie(doc):
    """Rend (page_du_bloc, rect_du_bloc, parent_de_page, pages_sans_objet)."""
    page_du_bloc, rect_du_bloc, parent_de_page = {}, {}, {}
    pages_rect, num, compte = [], 0, {}
    for sp in doc["spreads"]:
        for pg in sp["pages"]:
            num += 1
            pages_rect.append((sp["index"], pg["bounds"], num))
            parent_de_page[num] = pg.get("parent")
            compte[num] = 0
        for it in sp["items"]:
            b = it.get("bounds")
            if not b:
                continue
            rect_du_bloc[it["id"]] = b
            cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
            for (si, pb, nn) in pages_rect:
                if si == sp["index"] and pb[0] <= cx <= pb[2] and pb[1] <= cy <= pb[3]:
                    page_du_bloc[it["id"]] = nn
                    compte[nn] += 1
                    break
    sans_objet = {n for n in compte if compte[n] == 0}
    return page_du_bloc, rect_du_bloc, parent_de_page, sans_objet


def balayer(canal, progression):
    """Rend {page: {"style":…, "char":…, "texte":…, "vide":bool, "parent":…}}."""
    doc = canal.appel("document.inspect")
    page_du_bloc, rect, parent_de_page, sans_objet = geometrie(doc)

    blocs_texte = []
    for sp in doc["spreads"]:
        for it in sp["items"]:
            if it.get("story") is not None and it["id"] in page_du_bloc:
                blocs_texte.append(it["id"])

    profils = {n: {"style": None, "char": None, "texte": "",
                   "vide": True, "parent": parent_de_page.get(n)}
               for n in parent_de_page}

    total = len(blocs_texte)
    for i, fid in enumerate(blocs_texte, 1):
        b = rect[fid]
        point = [b[0] + 2.0, b[1] + 2.0]
        try:
            canal.cmd("text.selectAt", {"frame": fid, "point": point,
                                        "unit": "line"})
            a = canal.cmd("type.selectionAttrs") or {}
        except RuntimeError:
            continue
        page = page_du_bloc[fid]
        texte = (a.get("selectedText") or "").strip()
        p = profils[page]
        if p["style"] is None:
            p["style"] = a.get("paragraphStyle")
            p["char"] = a.get("characterStyle")
            p["texte"] = texte
        if texte:
            p["vide"] = False
        if i % 10 == 0 or i == total:
            progression(i, total)

    for n in sans_objet:
        profils[n]["vide"] = True
    return profils


# ------------------------------------------------------------ fenetre

class Fenetre(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Appliquer les gabarits par style — DesignCraft")
        self.resizable(False, False)
        self.canal = None
        self.profils = None
        self.file = queue.Queue()
        self.styles_para, self.styles_char, self.gabarits = [], [], []
        self._bati()
        self.after(100, self._vider_file)

    # -- construction
    def _bati(self):
        pad = {"padx": 8, "pady": 4}

        haut = ttk.Frame(self); haut.grid(row=0, column=0, sticky="we", **pad)
        ttk.Label(haut, text="Port :").pack(side="left")
        self.port = tk.StringVar(value=str(PORT_DEFAUT))
        ttk.Entry(haut, textvariable=self.port, width=7).pack(side="left", padx=4)
        ttk.Button(haut, text="Connecter", command=self.connecter).pack(side="left")
        self.etat = ttk.Label(haut, text="non connecte", foreground="#a00")
        self.etat.pack(side="left", padx=10)

        c1 = ttk.LabelFrame(self, text="Appliquer selon le style en tete de page")
        c1.grid(row=1, column=0, sticky="we", **pad)
        self.r_para = tk.BooleanVar(); self.r_char = tk.BooleanVar()
        self.v_para = tk.StringVar(); self.v_char = tk.StringVar()
        self.g_para = tk.StringVar(); self.g_char = tk.StringVar()
        self._ligne(c1, 0, "Style de paragraphe", self.r_para, self.v_para, self.g_para)
        self._ligne(c1, 1, "Style de caractere", self.r_char, self.v_char, self.g_char)

        c2 = ttk.LabelFrame(self, text="Appliquer a des pages particulieres")
        c2.grid(row=2, column=0, sticky="we", **pad)
        self.r_vide = tk.BooleanVar(); self.g_vide = tk.StringVar()
        self.r_pair = tk.BooleanVar(); self.g_pair = tk.StringVar()
        self.r_imp = tk.BooleanVar(); self.g_imp = tk.StringVar()
        self.r_tout = tk.BooleanVar(); self.g_tout = tk.StringVar()
        self.r_plage = tk.BooleanVar(); self.g_plage = tk.StringVar()
        self.v_de = tk.StringVar(value="1"); self.v_a = tk.StringVar(value="6")
        self._ligne(c2, 0, "Pages vides", self.r_vide, None, self.g_vide)
        self._ligne(c2, 1, "Pages paires", self.r_pair, None, self.g_pair)
        self._ligne(c2, 2, "Pages impaires", self.r_imp, None, self.g_imp)
        self._ligne(c2, 3, "Toutes les pages", self.r_tout, None, self.g_tout)
        self._ligne_plage(c2, 4)

        c3 = ttk.Frame(self); c3.grid(row=3, column=0, sticky="we", **pad)
        ttk.Button(c3, text="Balayer le document",
                   command=self.balayer).pack(side="left")
        self.barre = ttk.Progressbar(c3, length=240, mode="determinate")
        self.barre.pack(side="left", padx=8)
        self.compteur = ttk.Label(c3, text=""); self.compteur.pack(side="left")

        self.liste = tk.Text(self, height=14, width=78, font=("Consolas", 9))
        self.liste.grid(row=4, column=0, **pad)

        c4 = ttk.Frame(self); c4.grid(row=5, column=0, sticky="we", **pad)
        ttk.Button(c4, text="Apercu", command=self.apercu).pack(side="left")
        ttk.Button(c4, text="Appliquer", command=self.appliquer).pack(side="left", padx=6)
        ttk.Label(c4, text="   Prereglage :").pack(side="left")
        self.preset = ttk.Combobox(c4, width=18, state="readonly")
        self.preset.pack(side="left", padx=4)
        ttk.Button(c4, text="Charger", command=self.charger).pack(side="left")
        ttk.Button(c4, text="Enregistrer", command=self.enregistrer).pack(side="left", padx=4)
        ttk.Button(c4, text="Suppr.", command=self.supprimer).pack(side="left")
        self._lister_presets()

    def _ligne_plage(self, parent, rang):
        ttk.Checkbutton(parent, variable=self.r_plage).grid(row=rang, column=0, padx=4)
        ttk.Label(parent, text="Pages de / a", width=20,
                  anchor="w").grid(row=rang, column=1)
        boite = ttk.Frame(parent); boite.grid(row=rang, column=2, sticky="w", padx=4)
        ttk.Entry(boite, textvariable=self.v_de, width=6).pack(side="left")
        ttk.Label(boite, text=" a ").pack(side="left")
        ttk.Entry(boite, textvariable=self.v_a, width=6).pack(side="left")
        cbg = ttk.Combobox(parent, textvariable=self.g_plage, width=22,
                           state="readonly")
        cbg.grid(row=rang, column=3, padx=4)
        self._combos_gab.append(cbg)

    def _ligne(self, parent, rang, libelle, bool_var, style_var, gab_var):
        ttk.Checkbutton(parent, variable=bool_var).grid(row=rang, column=0, padx=4)
        ttk.Label(parent, text=libelle, width=20, anchor="w").grid(row=rang, column=1)
        if style_var is not None:
            cb = ttk.Combobox(parent, textvariable=style_var, width=24, state="readonly")
            cb.grid(row=rang, column=2, padx=4, pady=2)
            setattr(self, "cb_" + ("para" if "paragraphe" in libelle else "char"), cb)
        else:
            ttk.Label(parent, text="", width=26).grid(row=rang, column=2)
        cbg = ttk.Combobox(parent, textvariable=gab_var, width=22, state="readonly")
        cbg.grid(row=rang, column=3, padx=4)
        if not hasattr(self, "_combos_gab"):
            self._combos_gab = []
        self._combos_gab.append(cbg)

    # -- connexion
    def connecter(self):
        try:
            if self.canal:
                self.canal.fermer()
            self.canal = Canal(int(self.port.get()))
            doc = self.canal.appel("document.inspect")
        except Exception as e:
            self.etat.config(text="echec", foreground="#a00")
            messagebox.showerror("Connexion",
                "Impossible de joindre DesignCraft sur le port %s.\n\n%s\n\n"
                "L'application est-elle lancee avec --control %s ?"
                % (self.port.get(), e, self.port.get()))
            return
        self.styles_para = doc.get("paragraphStyles") or []
        self.styles_char = doc.get("characterStyles") or []
        self.gabarits = ["[None]"] + [p.get("label")
                                      for p in (doc.get("parents") or [])]
        self.cb_para["values"] = self.styles_para
        self.cb_char["values"] = self.styles_char
        for cb in self._combos_gab:
            cb["values"] = self.gabarits
        self.etat.config(text="%s — %d pages" % (doc.get("title") or "document",
                         doc.get("pageCount") or 0), foreground="#060")
        self.profils = None
        self.liste.delete("1.0", "end")
        self.liste.insert("end", "Connecte. Balayez le document pour relever "
                                 "les styles en tete de page.\n")

    # -- balayage
    def balayer(self):
        if not self.canal:
            messagebox.showwarning("Balayage", "Connectez-vous d'abord."); return
        self.liste.delete("1.0", "end")
        self.liste.insert("end", "Balayage en cours. Environ deux minutes "
                                 "pour un livre de 336 pages.\n")
        threading.Thread(target=self._balayer_fil, daemon=True).start()

    def _balayer_fil(self):
        try:
            p = balayer(self.canal, lambda i, t: self.file.put(("prog", i, t)))
            self.file.put(("fini", p, None))
        except Exception as e:
            self.file.put(("erreur", str(e), None))

    def _vider_file(self):
        try:
            while True:
                genre, a, b = self.file.get_nowait()
                if genre == "prog":
                    self.barre["maximum"] = b; self.barre["value"] = a
                    self.compteur.config(text="%d / %d" % (a, b))
                elif genre == "fini":
                    self.profils = a
                    self.compteur.config(text="termine")
                    self.apercu()
                elif genre == "erreur":
                    messagebox.showerror("Balayage", a)
        except queue.Empty:
            pass
        self.after(100, self._vider_file)

    # -- regles
    def _plan(self):
        if not self.profils:
            return None
        plan = {}
        def poser(pages, gab):
            if not gab:
                return
            for p in pages:
                plan[p] = gab
        toutes = sorted(self.profils)
        if self.r_tout.get():
            poser(toutes, self.g_tout.get())
        if self.r_pair.get():
            poser([p for p in toutes if p % 2 == 0], self.g_pair.get())
        if self.r_imp.get():
            poser([p for p in toutes if p % 2 == 1], self.g_imp.get())
        if self.r_plage.get():
            try:
                de, a = int(self.v_de.get()), int(self.v_a.get())
                poser([p for p in toutes if de <= p <= a], self.g_plage.get())
            except ValueError:
                pass
        if self.r_vide.get():
            poser([p for p in toutes if self.profils[p]["vide"]], self.g_vide.get())
        if self.r_char.get():
            poser([p for p in toutes
                   if self.profils[p]["char"] == self.v_char.get()], self.g_char.get())
        if self.r_para.get():
            poser([p for p in toutes
                   if self.profils[p]["style"] == self.v_para.get()], self.g_para.get())
        return plan

    def apercu(self):
        if not self.profils:
            messagebox.showwarning("Apercu", "Balayez le document d'abord."); return
        plan = self._plan()
        self.liste.delete("1.0", "end")
        styles = {}
        for p in self.profils.values():
            styles[p["style"]] = styles.get(p["style"], 0) + 1
        vides = sum(1 for p in self.profils.values() if p["vide"])
        self.liste.insert("end", "%d pages, %d vides.\n" % (len(self.profils), vides))
        self.liste.insert("end", "Styles en tete de page : %s\n\n" % ", ".join(
            "%s (%d)" % (k, v) for k, v in sorted(styles.items(),
                                                  key=lambda x: -x[1])[:8]))
        a_changer = [p for p in sorted(plan)
                     if self.profils[p]["parent"] != plan[p]]
        if not plan:
            self.liste.insert("end", "Aucune regle active.\n"); return
        self.liste.insert("end", "%d pages visees, %d a changer :\n\n"
                          % (len(plan), len(a_changer)))
        for p in sorted(plan):
            marque = "" if self.profils[p]["parent"] == plan[p] else "  <-"
            self.liste.insert("end", "  p.%-5d %-22s -> %-22s%s\n"
                              % (p, self.profils[p]["parent"], plan[p], marque))

    def appliquer(self):
        plan = self._plan()
        if not plan:
            messagebox.showwarning("Appliquer", "Rien a appliquer."); return
        a_changer = [p for p in sorted(plan) if self.profils[p]["parent"] != plan[p]]
        if not a_changer:
            messagebox.showinfo("Appliquer", "Tout est deja en place."); return
        if not messagebox.askyesno("Appliquer",
                "%d pages vont changer de gabarit.\n\nContinuer ?" % len(a_changer)):
            return
        par_gab = {}
        for p in a_changer:
            par_gab.setdefault(plan[p], []).append(p)
        try:
            for gab, pages in par_gab.items():
                self.canal.cmd("layout.pages.applyParent",
                               {"pages": [p - 1 for p in pages], "parent": gab})
            doc = self.canal.appel("document.inspect")
            _, _, parent_de_page, _ = geometrie(doc)
            for p in self.profils:
                self.profils[p]["parent"] = parent_de_page.get(p)
        except Exception as e:
            messagebox.showerror("Appliquer", str(e)); return
        rate = [p for p in a_changer if self.profils[p]["parent"] != plan[p]]
        self.apercu()
        if rate:
            messagebox.showwarning("Appliquer",
                "%d pages sur %d n'ont pas change : %s"
                % (len(rate), len(a_changer), rate[:12]))
        else:
            messagebox.showinfo("Appliquer",
                "%d pages ont recu leur gabarit." % len(a_changer))

    # -- prereglages
    def _tous_presets(self):
        if os.path.exists(FICHIER_PRESETS):
            try:
                return json.load(open(FICHIER_PRESETS, encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _lister_presets(self):
        self.preset["values"] = sorted(self._tous_presets())

    def _etat_courant(self):
        return {
            "para": [self.r_para.get(), self.v_para.get(), self.g_para.get()],
            "char": [self.r_char.get(), self.v_char.get(), self.g_char.get()],
            "vide": [self.r_vide.get(), self.g_vide.get()],
            "pair": [self.r_pair.get(), self.g_pair.get()],
            "imp":  [self.r_imp.get(), self.g_imp.get()],
            "tout": [self.r_tout.get(), self.g_tout.get()],
            "plage": [self.r_plage.get(), self.v_de.get(), self.v_a.get(),
                      self.g_plage.get()],
        }

    def enregistrer(self):
        nom = simpledialog.askstring("Prereglage", "Nom du prereglage :", parent=self)
        if not nom:
            return
        tous = self._tous_presets()
        tous[nom] = self._etat_courant()
        json.dump(tous, open(FICHIER_PRESETS, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        self._lister_presets()
        self.preset.set(nom)

    def charger(self):
        nom = self.preset.get()
        e = self._tous_presets().get(nom)
        if not e:
            return
        self.r_para.set(e["para"][0]); self.v_para.set(e["para"][1]); self.g_para.set(e["para"][2])
        self.r_char.set(e["char"][0]); self.v_char.set(e["char"][1]); self.g_char.set(e["char"][2])
        self.r_vide.set(e["vide"][0]); self.g_vide.set(e["vide"][1])
        self.r_pair.set(e["pair"][0]); self.g_pair.set(e["pair"][1])
        self.r_imp.set(e["imp"][0]);   self.g_imp.set(e["imp"][1])
        self.r_tout.set(e["tout"][0]); self.g_tout.set(e["tout"][1])
        pl = e.get("plage")
        if pl:
            self.r_plage.set(pl[0]); self.v_de.set(pl[1])
            self.v_a.set(pl[2]); self.g_plage.set(pl[3])
        if self.profils:
            self.apercu()

    def supprimer(self):
        nom = self.preset.get()
        tous = self._tous_presets()
        if nom in tous:
            del tous[nom]
            json.dump(tous, open(FICHIER_PRESETS, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            self._lister_presets(); self.preset.set("")


if __name__ == "__main__":
    Fenetre().mainloop()
