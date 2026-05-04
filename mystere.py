@group.command(name="mystere", description="🔢 Devine si ton nombre sera plus haut ou plus bas (1-14)")
    async def mystere(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 1, 2500, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        # --- ACTION : On retire la mise DIRECTEMENT ---
        self.update_money(interaction.user.id, -pari)

        # On génère les nombres (Banque et Joueur)
        bc = random.randint(1, 14)
        uc = random.randint(1, 14)
        # Sécurité : On s'assure que uc != bc pour éviter les égalités frustrantes au début
        while uc == bc:
            uc = random.randint(1, 14)

        embed = discord.Embed(
            title="🔢 JEU DU MYSTÈRE",
            description=(
                f"La banque a tiré le nombre : **{bc}**\n\n"
                f"Ton nombre est caché... 🕵️‍♂️\n"
                f"Sera-t-il **plus haut** ou **plus bas** que celui de la banque ?"
            ),
            color=0x3498DB
        )
        embed.set_footer(text="Fais ton choix avec les boutons ci-dessous !")
        embed.add_field(name="💰 Mise", value=f"**{self.fmt(pari)} €**", inline=True)
        embed.add_field(name="📈 Multiplicateur", value="**x2.0**", inline=True)

        class MystereView(discord.ui.View):
            def __init__(self, cog, bc, uc, pari, user):
                super().__init__(timeout=30)
                self.cog, self.bc, self.uc, self.pari, self.user = cog, bc, uc, pari, user

            async def on_timeout(self):
                # Si le temps expire, le pari est déjà perdu car retiré au début.
                pass

            async def process_choice(self, i: discord.Interaction, choice: str):
                if i.user.id != self.user.id: 
                    return await i.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)

                res_embed = discord.Embed(title="🔢 RÉSULTAT DU MYSTÈRE")
                res_embed.add_field(name="Banque", value=f"**{self.bc}**", inline=True)
                res_embed.add_field(name="Toi", value=f"**{self.uc}**", inline=True)
                
                # Logique de victoire
                win = (choice == "h" and self.uc > self.bc) or (choice == "b" and self.uc < self.bc)

                if win:
                    gain = self.pari * 2 # On rend la mise + le gain (x2)
                    self.cog.update_money(i.user.id, gain)
                    res_embed.color = 0x2ECC71
                    res_embed.description = f"### ✅ VICTOIRE !\nC'est passé ! Tu remportes **{self.cog.fmt(gain)} €**."
                else:
                    res_embed.color = 0xE74C3C
                    res_embed.description = f"### 💀 PERDU\nMauvais pronostic... Tu perds ta mise de **{self.cog.fmt(self.pari)} €**."

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PLUS HAUT", emoji="⏫", style=discord.ButtonStyle.success)
            async def plus_haut(self, i, b): await self.process_choice(i, "h")

            @discord.ui.button(label="PLUS BAS", emoji="⏬", style=discord.ButtonStyle.danger)
            async def plus_bas(self, i, b): await self.process_choice(i, "b")

        await interaction.response.send_message(embed=embed, view=MystereView(self, bc, uc, pari, interaction.user))
