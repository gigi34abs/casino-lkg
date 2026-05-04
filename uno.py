@group.command(name="uno", description="🃏 UNO Pro 2v2 : Le premier à vider sa main fait gagner son équipe !")
    async def uno(self, interaction: discord.Interaction, coequipier: discord.Member, adversaire1: discord.Member, adversaire2: discord.Member, mise: int):
        joueurs = [interaction.user, coequipier, adversaire1, adversaire2]
        
        if len(set(joueurs)) < 4: return await interaction.response.send_message("❌ 4 joueurs réels requis.", ephemeral=True)
        for p in joueurs:
            if self.get_user(p.id) < mise:
                return await interaction.response.send_message(f"❌ {p.display_name} n'a pas les fonds ({mise} €).", ephemeral=True)

        # Débit immédiat (Casino Rule)
        for p in joueurs: self.update_money(p.id, -mise)

        view = UnoView(self, joueurs, mise)
        await interaction.response.send_message(
            content=f"🃏 **PARTIE DE UNO LANCÉE** | Enjeu : **{self.fmt(mise*4)} €**\n🔵 **Équipe A** : {joueurs[0].mention} & {joueurs[1].mention}\n🔴 **Équipe B** : {joueurs[2].mention} & {joueurs[3].mention}",
            embed=view.make_embed(),
            view=view
        )

class UnoView(discord.ui.View):
    def __init__(self, cog, joueurs, mise):
        super().__init__(timeout=600)
        self.cog, self.joueurs, self.mise = cog, joueurs, mise
        self.couleurs = ["🟥", "🟦", "🟩", "🟨"]
        self.valeurs = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+2", "🚫", "🔄"]
        
        # Distribution (7 cartes comme en vrai)
        self.mains = {p.id: [f"{random.choice(self.couleurs)}{random.choice(self.valeurs)}" for _ in range(7)] for p in joueurs}
        # Ajout de 2 cartes Joker par joueur
        for p in joueurs: 
            if random.random() > 0.7: self.mains[p.id].append("🌈 Joker")
            if random.random() > 0.9: self.mains[p.id].append("🔥 +4")
            
        self.defausse = f"{random.choice(self.couleurs)}{random.choice(self.valeurs[:10])}"
        self.tour = 0
        self.direction = 1 # Pour le 🔄
        self.couleur_demandee = None # Pour le Joker/+4

    def make_embed(self):
        p_actuel = self.joueurs[self.tour]
        couleur_txt = self.couleur_demandee if self.couleur_demandee else self.defausse[0]
        
        embed = discord.Embed(title="🃏 TABLE DE UNO", description=f"Dernière carte : **{self.defausse}**\nCouleur active : **{couleur_txt}**", color=0x2b2d31)
        
        # Affichage des scores d'équipe
        score_a = len(self.mains[self.joueurs[0].id]) + len(self.mains[self.joueurs[1].id])
        score_b = len(self.mains[self.joueurs[2].id]) + len(self.mains[self.joueurs[3].id])
        
        embed.add_field(name="📊 Cartes restantes", value=f"🔵 Équipe A : `{score_a}`\n🔴 Équipe B : `{score_b}`", inline=False)
        embed.add_field(name="📍 C'est à toi", value=f"{p_actuel.mention}", inline=True)
        
        status = "\n".join([f"{'➡️' if i == self.tour else '👤'} {p.display_name} : {len(self.mains[p.id])} 🎴" for i, p in enumerate(self.joueurs)])
        embed.add_field(name="Joueurs", value=status, inline=True)
        
        return embed

    async def piocher(self, interaction):
        p_id = interaction.user.id
        self.mains[p_id].append(f"{random.choice(self.couleurs)}{random.choice(self.valeurs)}")
        self.tour = (self.tour + self.direction) % 4
        await interaction.response.edit_message(embed=self.make_embed(), view=UnoControl(self))

    async def jouer_carte(self, interaction, card_idx, nouvelle_couleur=None):
        p_id = interaction.user.id
        carte = self.mains[p_id].pop(card_idx)
        self.defausse = carte
        self.couleur_demandee = nouvelle_couleur # Utilisé si Joker

        # --- EFFETS ---
        skip = False
        pick = 0
        if "🚫" in carte: skip = True
        elif "🔄" in carte: self.direction *= -1
        elif "+2" in carte: pick = 2
        elif "+4" in carte: pick = 4; self.couleur_demandee = nouvelle_couleur
        elif "Joker" in carte: self.couleur_demandee = nouvelle_couleur
        else: self.couleur_demandee = None

        # --- VICTOIRE ---
        if len(self.mains[p_id]) == 0:
            gagnants = self.joueurs[0:2] if p_id in [self.joueurs[0].id, self.joueurs[1].id] else self.joueurs[2:4]
            total_gain = self.mise * 2
            for g in gagnants: self.cog.update_money(g.id, total_gain)
            
            emb = discord.Embed(title="🏆 UNO ! VICTOIRE FINALE !", description=f"L'équipe de **{interaction.user.mention}** gagne la partie !\n💰 Chaque membre reçoit : **{self.cog.fmt(total_gain)} €**", color=0xF1C40F)
            return await interaction.edit_original_response(embed=emb, view=None)

        # --- PROCHAIN TOUR ---
        self.tour = (self.tour + (self.direction * (2 if skip else 1))) % 4
        if pick > 0:
            victime = self.joueurs[self.tour].id
            for _ in range(pick): self.mains[victime].append(f"{random.choice(self.couleurs)}{random.choice(self.valeurs)}")
            self.tour = (self.tour + self.direction) % 4 # On saute le tour de celui qui a pioché

        await interaction.response.edit_message(embed=self.make_embed(), view=UnoControl(self))

class UnoControl(discord.ui.View):
    def __init__(self, parent):
        super().__init__(timeout=300)
        self.parent = parent
        self.setup_options()

    def setup_options(self):
        p_id = self.parent.joueurs[self.parent.tour].id
        main = self.parent.mains[p_id]
        couleur_active = self.parent.couleur_demandee if self.parent.couleur_demandee else self.parent.defausse[0]
        valeur_active = self.parent.defausse[1:]

        options = []
        for i, c in enumerate(main):
            # Logique de pose de carte
            jouable = ("Joker" in c or "+4" in c or c[0] == couleur_active or c[1:] == valeur_active)
            if jouable:
                options.append(discord.SelectOption(label=f"Jouer {c}", value=str(i)))

        if not options:
            options.append(discord.SelectOption(label="Aucune carte jouable (Piochez)", value="draw"))

        select = discord.ui.Select(placeholder="🎴 Choisis ta carte...", options=options[:25])
        
        async def callback(i):
            if i.user.id != p_id: return await i.response.send_message("❌ Patiente, ce n'est pas ton tour !", ephemeral=True)
            val = select.values[0]
            if val == "draw": return await self.parent.piocher(i)
            
            carte_choisie = main[int(val)]
            if "Joker" in carte_choisie or "+4" in carte_choisie:
                # Si c'est un joker, on demande la couleur avec un nouveau menu
                return await i.response.edit_message(content="🎨 **Choisis la nouvelle couleur :**", view=ColorPicker(self.parent, int(val)))
            
            await self.parent.jouer_carte(i, int(val))

        select.callback = callback
        self.add_item(select)

    @discord.ui.button(label="Voir ma main", emoji="👁️", style=discord.ButtonStyle.gray)
    async def show(self, i, b):
        m = self.parent.mains.get(i.user.id, [])
        await i.response.send_message(f"🃏 Ta main : **{' | '.join(m)}**", ephemeral=True)

class ColorPicker(discord.ui.View):
    def __init__(self, parent, card_idx):
        super().__init__(timeout=60)
        self.parent, self.idx = parent, card_idx

    async def pick(self, i, color):
        await self.parent.jouer_carte(i, self.idx, color)

    @discord.ui.button(label="Rouge", emoji="🟥")
    async def r(self, i, b): await self.pick(i, "🟥")
    @discord.ui.button(label="Bleu", emoji="🟦")
    async def b(self, i, b): await self.pick(i, "🟦")
    @discord.ui.button(label="Vert", emoji="🟩")
    async def v(self, i, b): await self.pick(i, "🟩")
    @discord.ui.button(label="Jaune", emoji="🟨")
    async def j(self, i, b): await self.pick(i, "🟨")
