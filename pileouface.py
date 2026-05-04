@group.command(name="pileouface", description="🪙 Tente de doubler ta mise sur un lancer de pièce !")
    async def pileouface(self, interaction: discord.Interaction, pari: int):
        # --- VÉRIFICATIONS ---
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 10, 10000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        # --- ACTION : On retire la mise DIRECTEMENT ---
        self.update_money(interaction.user.id, -pari)

        # On prépare l'embed de choix
        embed = discord.Embed(
            title="🪙 PILE OU FACE",
            description=f"Mise : **{self.fmt(pari)} €**\n\nFais ton choix en cliquant sur un bouton !",
            color=0xF1C40F
        )
        
        # --- LA VUE AVEC LES BOUTONS ---
        class PFView(discord.ui.View):
            def __init__(self, cog, user, pari):
                super().__init__(timeout=60)
                self.cog, self.user, self.pari = cog, user, pari

            async def jouer(self, i, choix):
                if i.user.id != self.user.id: return
                
                # Désactive les boutons après le clic
                for b in self.children: b.disabled = True
                
                # Animation
                await i.response.edit_message(content="🪙 *La pièce tourne...*", embed=None, view=self)
                await asyncio.sleep(2)
                
                # Résultat
                resultat = random.choice(["pile", "face"])
                win = (choix == resultat)
                
                res_embed = discord.Embed(title="🪙 RÉSULTAT")
                if win:
                    gain = self.pari * 2
                    self.cog.update_money(self.user.id, gain)
                    res_embed.color = 0x2ECC71
                    res_embed.description = f"### ✅ C'EST {resultat.upper()} !\n\nBravo ! Tu remportes **{self.cog.fmt(gain)} €** !"
                else:
                    res_embed.color = 0xE74C3C
                    res_embed.description = f"### 💀 C'EST {resultat.upper()}...\n\nPerdu ! Tu perds ta mise de **{self.cog.fmt(self.pari)} €**."
                
                await i.edit_original_response(content=None, embed=res_embed, view=None)

            @discord.ui.button(label="PILE", style=discord.ButtonStyle.primary, emoji="🪙")
            async def pile(self, i, b): await self.jouer(i, "pile")

            @discord.ui.button(label="FACE", style=discord.ButtonStyle.secondary, emoji="👤")
            async def face(self, i, b): await self.jouer(i, "face")

        await interaction.response.send_message(embed=embed, view=PFView(self, interaction.user, pari))
