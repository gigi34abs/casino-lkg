@group.command(name="risque", description="🏔️ Survis à 5 étapes mortelles pour gagner 500 € ! (Mise fixe : 65 €)")
    async def risque(self, interaction: discord.Interaction, mise: int):
        # --- CONDITION DE MISE STRICTE ---
        if mise != 65:
            return await interaction.response.send_message("⚠️ **Refusé** : Le jeu **RISQUE** nécessite une mise précise de **65 €**.", ephemeral=True)

        solde = self.get_user(interaction.user.id)
        if solde < mise:
            return await interaction.response.send_message("❌ Tu n'as pas les 65 € nécessaires.", ephemeral=True)

        # Prélèvement immédiat
        self.update_money(interaction.user.id, -65)

        view = RisqueView(self, interaction.user)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

class RisqueView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=120)
        self.cog = cog
        self.user = user
        self.niveau = 1
        # Config : bombes, gain de l'étape, nombre de cases
        self.config = {
            1: {"b": 1, "g": 10, "c": 5},
            2: {"b": 2, "g": 15, "c": 5},
            3: {"b": 3, "g": 70, "c": 5},
            4: {"b": 4, "g": 200, "c": 5},
            5: {"b": 1, "g": 500, "c": 2}
        }
        self.cagnotte = 0

    def make_embed(self):
        conf = self.config[self.niveau]
        progression = "▰" * self.niveau + "▱" * (5 - self.niveau)
        
        embed = discord.Embed(
            title="☢️ MODE RISQUE",
            description=(
                f"**Niveau {self.niveau}/5**\n`{progression}`\n\n"
                f"Il y a **{conf['b']} bombe(s)** cachée(s) parmi **{conf['c']} cases**.\n"
                f"Si tu réussis, tu gagnes **+{conf['g']} €**."
            ),
            color=0xF39C12
        )
        embed.add_field(name="💰 Cagnotte actuelle", value=f"**{self.cog.fmt(self.cagnotte)} €**")
        embed.set_footer(text="Attention : Un seul faux pas et tout est perdu !")
        return embed

    async def check_step(self, interaction, choice):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Ce n'est pas ta partie.", ephemeral=True)

        conf = self.config[self.niveau]
        # On place les bombes
        bombes = random.sample(range(1, conf['c'] + 1), conf['b'])

        if choice in bombes:
            # PERDU
            embed = discord.Embed(
                title="💥 BOUM ! TERMINÉ.",
                description=f"Tu as touché une mine au niveau {self.niveau}.\nTu perds tes **65 €** et ta progression.",
                color=0xC0392B
            )
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            # GAGNÉ
            self.cagnotte += conf['g']
            
            if self.niveau < 5:
                self.niveau += 1
                # On met à jour les boutons pour le prochain niveau
                new_view = RisqueButtons(self)
                await interaction.response.edit_message(embed=self.make_embed(), view=new_view)
            else:
                # VICTOIRE FINALE
                self.cog.update_money(self.user.id, self.cagnotte)
                embed = discord.Embed(
                    title="🏆 L'ULTIME SURVIVANT !",
                    description=f"Tu as bravé tous les dangers !\n\nTotal remporté : **{self.cog.fmt(self.cagnotte)} €**",
                    color=0x27AE60
                )
                await interaction.response.edit_message(embed=embed, view=None)

class RisqueButtons(discord.ui.View):
    def __init__(self, parent):
        super().__init__(timeout=120)
        self.parent = parent
        nb_cases = self.parent.config[self.parent.niveau]["c"]
        
        for i in range(1, nb_cases + 1):
            btn = discord.ui.Button(
                label=f"Case {i}", 
                style=discord.ButtonStyle.primary if nb_cases > 2 else discord.ButtonStyle.danger,
                custom_id=str(i)
            )
            btn.callback = self.get_callback(i)
            self.add_item(btn)

    def get_callback(self, i):
        async def callback(interaction):
            await self.parent.check_step(interaction, i)
        return callback
