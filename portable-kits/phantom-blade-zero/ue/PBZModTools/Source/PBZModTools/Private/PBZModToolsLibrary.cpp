#include "PBZModToolsLibrary.h"

#include "Modules/ModuleManager.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "PhysicsAssetUtils.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimCurveMetadata.h"
#include "Animation/MorphTarget.h"
#include "AnimationRuntime.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Materials/MaterialInstanceConstant.h"
#include "ClothingAsset.h"
#include "ClothingAssetFactory.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "JsonObjectConverter.h"
#include "Engine/Texture.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_CopyPoseFromMesh.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_LayeredBoneBlend.h"
#include "AnimGraphNode_Slot.h"
#include "EdGraph/EdGraph.h"
#include "EdGraphSchema_K2.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "K2Node_Event.h"
#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Kismet/KismetMathLibrary.h"
#include "Kismet/KismetStringLibrary.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet/GameplayStatics.h"
#include "Components/SkeletalMeshComponent.h"
#include "Editor.h"
#include "Components/ActorComponent.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, PBZModTools)

namespace
{
	TSharedPtr<FJsonObject> ParseJson(const FString& Json)
	{
		TSharedPtr<FJsonObject> Root;
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
		FJsonSerializer::Deserialize(Reader, Root);
		return Root;
	}

	FVector ReadVec(const TSharedPtr<FJsonObject>& O, const TCHAR* Field, const FVector& Default)
	{
		const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
		if (O->TryGetArrayField(Field, Arr) && Arr->Num() == 3)
		{
			return FVector((*Arr)[0]->AsNumber(), (*Arr)[1]->AsNumber(), (*Arr)[2]->AsNumber());
		}
		return Default;
	}

	FString TransformToJson(const FTransform& T)
	{
		const FVector L = T.GetLocation();
		const FQuat Q = T.GetRotation();
		const FVector S = T.GetScale3D();
		return FString::Printf(TEXT("\"t\":[%.4f,%.4f,%.4f],\"q\":[%.6f,%.6f,%.6f,%.6f],\"s\":[%.4f,%.4f,%.4f]"),
			L.X, L.Y, L.Z, Q.X, Q.Y, Q.Z, Q.W, S.X, S.Y, S.Z);
	}
}

UPhysicsAsset* UPBZModToolsLibrary::CreatePhysicsAsset(const FString& PackagePath, const FString& Name, USkeletalMesh* PreviewMesh)
{
	const FString LongName = PackagePath / Name;
	if (UPhysicsAsset* Existing = LoadObject<UPhysicsAsset>(nullptr, *(LongName + TEXT(".") + Name), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		return Existing;
	}
	UPackage* Package = CreatePackage(*LongName);
	UPhysicsAsset* PA = NewObject<UPhysicsAsset>(Package, *Name, RF_Public | RF_Standalone | RF_Transactional);
	if (PreviewMesh)
	{
		PA->SetPreviewMesh(PreviewMesh);
	}
	FAssetRegistryModule::AssetCreated(PA);
	PA->MarkPackageDirty();
	return PA;
}

FString UPBZModToolsLibrary::BuildPhysicsAsset(UPhysicsAsset* PA, USkeletalMesh* Mesh, const FString& Json)
{
	if (!PA || !Mesh)
	{
		return TEXT("ERROR: null asset");
	}
	TSharedPtr<FJsonObject> Root = ParseJson(Json);
	if (!Root.IsValid())
	{
		return TEXT("ERROR: bad json");
	}
	PA->Modify();
	while (PA->SkeletalBodySetups.Num() > 0)
	{
		FPhysicsAssetUtils::DestroyBody(PA, PA->SkeletalBodySetups.Num() - 1);
	}
	while (PA->ConstraintSetup.Num() > 0)
	{
		FPhysicsAssetUtils::DestroyConstraint(PA, PA->ConstraintSetup.Num() - 1);
	}

	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	FPhysAssetCreateParams CreateParams;
	int32 Made = 0;
	const TArray<TSharedPtr<FJsonValue>>* Bodies = nullptr;
	if (Root->TryGetArrayField(TEXT("bodies"), Bodies))
	{
		for (const TSharedPtr<FJsonValue>& V : *Bodies)
		{
			TSharedPtr<FJsonObject> B = V->AsObject();
			const FName Bone(*B->GetStringField(TEXT("bone")));
			if (Ref.FindBoneIndex(Bone) == INDEX_NONE)
			{
				return FString::Printf(TEXT("ERROR: bone %s not in mesh"), *Bone.ToString());
			}
			const int32 Index = FPhysicsAssetUtils::CreateNewBody(PA, Bone, CreateParams);
			USkeletalBodySetup* Setup = PA->SkeletalBodySetups[Index];
			Setup->AggGeom.EmptyElements();
			const FString Type = B->GetStringField(TEXT("type"));
			const FVector Center = ReadVec(B, TEXT("center"), FVector::ZeroVector);
			const FVector Rot = ReadVec(B, TEXT("rotation"), FVector::ZeroVector);
			FRotator Rotator(Rot.X, Rot.Y, Rot.Z);
			const TArray<TSharedPtr<FJsonValue>>* QuatArr = nullptr;
			if (B->TryGetArrayField(TEXT("quat"), QuatArr) && QuatArr->Num() == 4)
			{
				Rotator = FQuat((*QuatArr)[0]->AsNumber(), (*QuatArr)[1]->AsNumber(), (*QuatArr)[2]->AsNumber(), (*QuatArr)[3]->AsNumber()).GetNormalized().Rotator();
			}
			if (Type == TEXT("sphere"))
			{
				FKSphereElem E(B->GetNumberField(TEXT("radius")));
				E.Center = Center;
				Setup->AggGeom.SphereElems.Add(E);
			}
			else if (Type == TEXT("box"))
			{
				const FVector Ext = ReadVec(B, TEXT("extent"), FVector(10, 10, 10));
				FKBoxElem E(Ext.X, Ext.Y, Ext.Z);
				E.Center = Center;
				E.Rotation = Rotator;
				Setup->AggGeom.BoxElems.Add(E);
			}
			else
			{
				FKSphylElem E(B->GetNumberField(TEXT("radius")), B->GetNumberField(TEXT("length")));
				E.Center = Center;
				E.Rotation = Rotator;
				Setup->AggGeom.SphylElems.Add(E);
			}
			bool bKinematic = true;
			B->TryGetBoolField(TEXT("kinematic"), bKinematic);
			Setup->PhysicsType = bKinematic ? PhysType_Kinematic : PhysType_Simulated;
			double Mass = 0.0;
			if (B->TryGetNumberField(TEXT("mass"), Mass) && Mass > 0.0)
			{
				Setup->DefaultInstance.SetMassOverride(Mass, true);
			}
			double Damp = 0.0;
			if (B->TryGetNumberField(TEXT("lin_damp"), Damp))
			{
				Setup->DefaultInstance.LinearDamping = Damp;
			}
			if (B->TryGetNumberField(TEXT("ang_damp"), Damp))
			{
				Setup->DefaultInstance.AngularDamping = Damp;
			}
			++Made;
		}
	}

	int32 Joints = 0;
	const TArray<TSharedPtr<FJsonValue>>* Explicit = nullptr;
	if (Root->TryGetArrayField(TEXT("joints"), Explicit))
	{
		TArray<FTransform> CS;
		FAnimationRuntime::FillUpComponentSpaceTransforms(Ref, Ref.GetRefBonePose(), CS);
		for (const TSharedPtr<FJsonValue>& V : *Explicit)
		{
			TSharedPtr<FJsonObject> J = V->AsObject();
			const FName Child(*J->GetStringField(TEXT("child")));
			const FName Parent(*J->GetStringField(TEXT("parent")));
			const int32 ChildBody = PA->FindBodyIndex(Child);
			const int32 ParentBody = PA->FindBodyIndex(Parent);
			if (ChildBody == INDEX_NONE || ParentBody == INDEX_NONE)
			{
				return FString::Printf(TEXT("ERROR: joint %s-%s has no bodies"), *Child.ToString(), *Parent.ToString());
			}
			const FTransform RelTM = CS[Ref.FindBoneIndex(Child)].GetRelativeTransform(CS[Ref.FindBoneIndex(Parent)]);
			const int32 CIdx = FPhysicsAssetUtils::CreateNewConstraint(PA, Child);
			UPhysicsConstraintTemplate* T = PA->ConstraintSetup[CIdx];
			FConstraintInstance& Inst = T->DefaultInstance;
			Inst.ConstraintBone1 = Child;
			Inst.Pos1 = FVector::ZeroVector;
			Inst.PriAxis1 = FVector(1, 0, 0);
			Inst.SecAxis1 = FVector(0, 1, 0);
			Inst.ConstraintBone2 = Parent;
			Inst.Pos2 = RelTM.GetLocation();
			Inst.PriAxis2 = RelTM.GetUnitAxis(EAxis::X);
			Inst.SecAxis2 = RelTM.GetUnitAxis(EAxis::Y);
			Inst.SetLinearXMotion(LCM_Locked);
			Inst.SetLinearYMotion(LCM_Locked);
			Inst.SetLinearZMotion(LCM_Locked);
			Inst.SetAngularSwing1Limit(ACM_Limited, J->GetNumberField(TEXT("swing1")));
			Inst.SetAngularSwing2Limit(ACM_Limited, J->GetNumberField(TEXT("swing2")));
			Inst.SetAngularTwistLimit(ACM_Limited, J->GetNumberField(TEXT("twist")));
			double Stiff = 0.0, DriveDamp = 0.0;
			J->TryGetNumberField(TEXT("drive_stiffness"), Stiff);
			J->TryGetNumberField(TEXT("drive_damping"), DriveDamp);
			if (Stiff > 0.0 || DriveDamp > 0.0)
			{
				Inst.SetAngularDriveMode(EAngularDriveMode::SLERP);
				Inst.SetOrientationDriveSLERP(Stiff > 0.0);
				Inst.SetAngularVelocityDriveSLERP(DriveDamp > 0.0);
				Inst.SetAngularDriveParams(Stiff, DriveDamp, 0.f);
				Inst.SetAngularOrientationTarget(FQuat::Identity);
			}
			T->SetDefaultProfile(Inst);
			PA->DisableCollision(ChildBody, ParentBody);
			++Joints;
		}
	}
	const TArray<TSharedPtr<FJsonValue>>* Pairs = nullptr;
	if (Root->TryGetArrayField(TEXT("disable_pairs"), Pairs))
	{
		for (const TSharedPtr<FJsonValue>& V : *Pairs)
		{
			const TArray<TSharedPtr<FJsonValue>>& P = V->AsArray();
			const int32 IA = PA->FindBodyIndex(FName(*P[0]->AsString()));
			const int32 IB = PA->FindBodyIndex(FName(*P[1]->AsString()));
			if (IA != INDEX_NONE && IB != INDEX_NONE)
			{
				PA->DisableCollision(IA, IB);
			}
		}
	}

	PA->UpdateBodySetupIndexMap();
	PA->UpdateBoundsBodiesArray();
	PA->SetPreviewMesh(Mesh);
	PA->PostEditChange();
	PA->MarkPackageDirty();
	return FString::Printf(TEXT("ok bodies=%d constraints=%d"), Made, Joints);
}

FString UPBZModToolsLibrary::SetMorphCurveMetaData(USkeletalMesh* Mesh, const TArray<FString>& CurveNames)
{
	if (!Mesh)
	{
		return TEXT("ERROR: null mesh");
	}
	Mesh->Modify();
	UAnimCurveMetaData* Meta = Mesh->GetAssetUserData<UAnimCurveMetaData>();
	if (!Meta)
	{
		Meta = NewObject<UAnimCurveMetaData>(Mesh, NAME_None, RF_Transactional);
		Mesh->AddAssetUserData(Meta);
	}
	int32 Flagged = 0;
	for (const FString& N : CurveNames)
	{
		const FName Curve(*N);
		Meta->AddCurveMetaData(Curve);
		if (FCurveMetaData* Data = Meta->GetCurveMetaData(Curve))
		{
			Data->Type.bMorphtarget = true;
			++Flagged;
		}
	}
	Mesh->MarkPackageDirty();
	return FString::Printf(TEXT("ok flagged=%d total=%d"), Flagged, Meta->GetNumCurveMetaData());
}

FString UPBZModToolsLibrary::DumpRefSkeleton(USkeletalMesh* Mesh)
{
	if (!Mesh)
	{
		return TEXT("[]");
	}
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	const TArray<FTransform>& Pose = Ref.GetRefBonePose();
	FString Out = TEXT("[");
	for (int32 i = 0; i < Ref.GetNum(); ++i)
	{
		Out += FString::Printf(TEXT("%s{\"name\":\"%s\",\"parent\":%d,%s}"), i ? TEXT(",") : TEXT(""),
			*Ref.GetBoneName(i).ToString(), Ref.GetParentIndex(i), *TransformToJson(Pose[i]));
	}
	return Out + TEXT("]");
}

TArray<FString> UPBZModToolsLibrary::GetMorphTargetNames(USkeletalMesh* Mesh)
{
	TArray<FString> Out;
	if (Mesh)
	{
		for (const UMorphTarget* M : Mesh->GetMorphTargets())
		{
			if (M)
			{
				Out.Add(M->GetName());
			}
		}
	}
	return Out;
}

void UPBZModToolsLibrary::SetPostProcessAnimBlueprint(USkeletalMesh* Mesh, UClass* AnimClass)
{
	if (!Mesh)
	{
		return;
	}
	Mesh->Modify();
	Mesh->SetPostProcessAnimBlueprint(AnimClass);
	Mesh->MarkPackageDirty();
}

void UPBZModToolsLibrary::SetMeshPhysicsAsset(USkeletalMesh* Mesh, UPhysicsAsset* PhysicsAsset)
{
	if (!Mesh)
	{
		return;
	}
	Mesh->Modify();
	Mesh->SetPhysicsAsset(PhysicsAsset);
	Mesh->MarkPackageDirty();
}

FString UPBZModToolsLibrary::DumpSections(USkeletalMesh* Mesh)
{
	if (!Mesh || !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.Num() == 0)
	{
		return TEXT("[]");
	}
	const FSkeletalMeshLODModel& Lod = Mesh->GetImportedModel()->LODModels[0];
	const TArray<FSkeletalMaterial>& Mats = Mesh->GetMaterials();
	FString Out = TEXT("{\"sections\":[");
	for (int32 i = 0; i < Lod.Sections.Num(); ++i)
	{
		const FSkelMeshSection& S = Lod.Sections[i];
		const FName Slot = Mats.IsValidIndex(S.MaterialIndex) ? Mats[S.MaterialIndex].MaterialSlotName : NAME_None;
		Out += FString::Printf(TEXT("%s{\"section\":%d,\"material\":%d,\"slot\":\"%s\",\"verts\":%d,\"tris\":%d,\"bones\":%d,\"max_influences\":%d}"),
			i ? TEXT(",") : TEXT(""), i, S.MaterialIndex, *Slot.ToString(), S.GetNumVertices(), S.NumTriangles, S.BoneMap.Num(), S.MaxBoneInfluences);
	}
	return Out + TEXT("]}");
}

namespace
{
	FMaterialParameterInfo ParamInfo(const FString& Name, int32 Association, int32 Index)
	{
		const EMaterialParameterAssociation A = Association == 1 ? EMaterialParameterAssociation::LayerParameter
			: Association == 2 ? EMaterialParameterAssociation::BlendParameter : EMaterialParameterAssociation::GlobalParameter;
		return FMaterialParameterInfo(FName(*Name), A, A == EMaterialParameterAssociation::GlobalParameter ? INDEX_NONE : Index);
	}
}

void UPBZModToolsLibrary::ClearMaterialInstanceParameters(UMaterialInstanceConstant* Instance)
{
	if (Instance)
	{
		Instance->Modify();
		Instance->ClearParameterValuesEditorOnly();
		Instance->MarkPackageDirty();
	}
}

void UPBZModToolsLibrary::SetMaterialTextureParameter(UMaterialInstanceConstant* Instance, const FString& Name, int32 Association, int32 Index, UTexture* Value)
{
	if (Instance)
	{
		Instance->SetTextureParameterValueEditorOnly(ParamInfo(Name, Association, Index), Value);
		Instance->MarkPackageDirty();
	}
}

void UPBZModToolsLibrary::SetMaterialScalarParameter(UMaterialInstanceConstant* Instance, const FString& Name, int32 Association, int32 Index, float Value)
{
	if (Instance)
	{
		Instance->SetScalarParameterValueEditorOnly(ParamInfo(Name, Association, Index), Value);
		Instance->MarkPackageDirty();
	}
}

void UPBZModToolsLibrary::SetMaterialVectorParameter(UMaterialInstanceConstant* Instance, const FString& Name, int32 Association, int32 Index, FLinearColor Value)
{
	if (Instance)
	{
		Instance->SetVectorParameterValueEditorOnly(ParamInfo(Name, Association, Index), Value);
		Instance->MarkPackageDirty();
	}
}

FString UPBZModToolsLibrary::DumpMaterialInstanceParameters(UMaterialInstanceConstant* Instance)
{
	if (!Instance)
	{
		return TEXT("[]");
	}
	FString Out = TEXT("[");
	auto Add = [&Out](const TCHAR* Kind, const FMaterialParameterInfo& I, const FString& V)
	{
		Out += FString::Printf(TEXT("%s{\"kind\":\"%s\",\"name\":\"%s\",\"assoc\":%d,\"index\":%d,\"value\":\"%s\"}"),
			Out.Len() > 1 ? TEXT(",") : TEXT(""), Kind, *I.Name.ToString(), (int32)I.Association, I.Index, *V);
	};
	for (const FTextureParameterValue& P : Instance->TextureParameterValues) { Add(TEXT("texture"), P.ParameterInfo, P.ParameterValue ? P.ParameterValue->GetPathName() : TEXT("null")); }
	for (const FScalarParameterValue& P : Instance->ScalarParameterValues) { Add(TEXT("scalar"), P.ParameterInfo, FString::SanitizeFloat(P.ParameterValue)); }
	for (const FVectorParameterValue& P : Instance->VectorParameterValues) { Add(TEXT("vector"), P.ParameterInfo, P.ParameterValue.ToString()); }
	return Out + TEXT("]");
}

namespace
{
	int32 FindSectionBySlot(USkeletalMesh* Mesh, const FString& Slot)
	{
		const FSkeletalMeshLODModel& Lod = Mesh->GetImportedModel()->LODModels[0];
		const TArray<FSkeletalMaterial>& Mats = Mesh->GetMaterials();
		for (int32 i = 0; i < Lod.Sections.Num(); ++i)
		{
			const int32 Mat = Lod.Sections[i].MaterialIndex;
			if (Mats.IsValidIndex(Mat) && Mats[Mat].MaterialSlotName.ToString() == Slot)
			{
				return i;
			}
		}
		return INDEX_NONE;
	}
}

FString UPBZModToolsLibrary::CreateClothFromSlot(USkeletalMesh* Mesh, const FString& Slot, const FString& Name, UPhysicsAsset* CollisionAsset,
	float MaxDistance, const FString& MaskJson, const FString& ConfigJson)
{
	if (!Mesh || !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.Num() == 0)
	{
		return TEXT("ERROR: invalid mesh");
	}
	TSharedPtr<FJsonObject> Mask = ParseJson(MaskJson);
	TSharedPtr<FJsonObject> Config = ConfigJson.IsEmpty() ? MakeShared<FJsonObject>() : ParseJson(ConfigJson);
	if (!Mask.IsValid() || !Config.IsValid())
	{
		return TEXT("ERROR: bad json");
	}
	TArray<FVector> Anchors;
	const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
	if (Mask->TryGetArrayField(TEXT("anchors"), Arr))
	{
		for (const TSharedPtr<FJsonValue>& V : *Arr)
		{
			const TArray<TSharedPtr<FJsonValue>>& P = V->AsArray();
			Anchors.Add(FVector(P[0]->AsNumber(), P[1]->AsNumber(), P[2]->AsNumber()));
		}
	}
	if (Anchors.Num() == 0)
	{
		return TEXT("ERROR: no anchors");
	}
	const bool bPlane = Mask->GetStringField(TEXT("type")) == TEXT("plane");
	const FVector Dir = ReadVec(Mask, TEXT("dir"), FVector(0, 0, -1)).GetSafeNormal();
	const double D0 = Mask->GetNumberField(TEXT("d0"));
	const double D1 = FMath::Max(Mask->GetNumberField(TEXT("d1")), D0 + 0.01);
	// Optional "sim_slot": the clothing is simulated on that section and Slot's section is bound to it (mesh-to-mesh), e.g.
	// a smooth shell driving a pleated skirt, whose normals would otherwise be rebuilt from the welded pleat folds. The
	// shell is disabled for rendering first, in a rebuild of its own, as the editor does for "Remove from mesh" (the used
	// bone array has to reflect it).
	FString SimSlot;
	if (Mask->TryGetStringField(TEXT("sim_slot"), SimSlot))
	{
		const int32 SimSection = FindSectionBySlot(Mesh, SimSlot);
		if (SimSection == INDEX_NONE)
		{
			return FString::Printf(TEXT("ERROR: no section for sim slot %s"), *SimSlot);
		}
		FScopedSkeletalMeshPostEditChange ScopedPostEditChange(Mesh);
		Mesh->Modify();
		Mesh->RemoveMeshSection(0, SimSection);
	}
	FString Result;
	{
		// Defer the LOD rebuild until the binding is recorded in UserSectionsData (else the rebuild drops it).
		FScopedSkeletalMeshPostEditChange ScopedPostEditChange(Mesh);
		Mesh->Modify();
		const int32 Section = FindSectionBySlot(Mesh, Slot);
		if (Section == INDEX_NONE)
		{
			return FString::Printf(TEXT("ERROR: no section for slot %s"), *Slot);
		}
		const int32 SimSection = SimSlot.IsEmpty() ? Section : FindSectionBySlot(Mesh, SimSlot);
		if (SimSection == INDEX_NONE || (!SimSlot.IsEmpty() && SimSection == Section))
		{
			return FString::Printf(TEXT("ERROR: bad sim slot %s"), *SimSlot);
		}
		FSkeletalMeshClothBuildParams Params;
		Params.AssetName = Name;
		Params.LodIndex = 0;
		Params.SourceSection = SimSection;
		Params.bRemoveFromMesh = false;
		Params.PhysicsAsset = CollisionAsset;
		UClothingAssetFactory* Factory = GetMutableDefault<UClothingAssetFactory>();
		UClothingAssetCommon* Asset = Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(Mesh, Params));
		if (!Asset)
		{
			return TEXT("ERROR: CreateFromSkeletalMesh failed");
		}
		Mesh->AddClothingAsset(Asset);
		if (UChaosClothConfig* Chaos = Asset->GetClothConfig<UChaosClothConfig>())
		{
			if (Config->Values.Num() > 0)
			{
				FJsonObjectConverter::JsonObjectToUStruct(Config.ToSharedRef(), UChaosClothConfig::StaticClass(), Chaos, 0, 0);
			}
		}
		FClothLODDataCommon& ClothLod = Asset->LodData[0];
		FClothPhysicalMeshData& Phys = ClothLod.PhysicalMeshData;
		const int32 NumVerts = Phys.Vertices.Num();
		ClothLod.PointWeightMaps.Reset();
		ClothLod.PointWeightMaps.Reserve(3);   // MaxMask stays referenced while the backstop maps are added
		ClothLod.PointWeightMaps.AddDefaulted();
		FPointWeightMap& MaxMask = ClothLod.PointWeightMaps.Last();
		MaxMask.Initialize(NumVerts);
		MaxMask.Name = TEXT("MaxDistance");
		MaxMask.CurrentTarget = (uint8)EWeightMapTargetCommon::MaxDistance;
		MaxMask.bEnabled = true;
		int32 NumFixed = 0;
		float MaxSeen = 0.f;
		for (int32 i = 0; i < NumVerts; ++i)
		{
			const FVector P = (FVector)Phys.Vertices[i];
			double T = TNumericLimits<double>::Max();
			for (const FVector& A : Anchors)
			{
				T = FMath::Min(T, bPlane ? FVector::DotProduct(P - A, Dir) : FVector::Distance(P, A));
			}
			const float V = (float)(FMath::Clamp((T - D0) / (D1 - D0), 0.0, 1.0) * MaxDistance);
			MaxMask.Values[i] = V;
			MaxSeen = FMath::Max(MaxSeen, V);
			NumFixed += V <= 0.1f ? 1 : 0;
		}
		// Optional backstop, mask "backstop": {"distance": cm, "radius": cm, "axis": [x, y, z], "min_dot": d}: a sphere behind
		// each free particle (against its skinned normal) that the particle may not enter, so the cloth cannot sink inward of
		// its skinned surface. Only where the import normal points away from the vertical axis through "axis" by more than
		// min_dot (an inward-facing pleat wall would be pushed into the body).
		int32 NumBackstop = 0;
		const TSharedPtr<FJsonObject>* Backstop = nullptr;
		if (Mask->TryGetObjectField(TEXT("backstop"), Backstop))
		{
			const float BDist = (float)(*Backstop)->GetNumberField(TEXT("distance"));
			const float BRadius = (float)(*Backstop)->GetNumberField(TEXT("radius"));
			const double MinDot = (*Backstop)->GetNumberField(TEXT("min_dot"));
			const FVector Axis = ReadVec(*Backstop, TEXT("axis"), FVector::ZeroVector);
			// The import normal of a welded particle is the render normal of one of its source verts (on a pleated skirt
			// often a pleat wall facing sideways); the backstop (skinned Phys.Normals) uses the area-weighted normal of the
			// cloth surface instead, oriented like the import normals.
			TArray<FVector3f> Smooth;
			Smooth.SetNumZeroed(NumVerts);
			for (int32 t = 0; t + 2 < Phys.Indices.Num(); t += 3)
			{
				const uint32 A = Phys.Indices[t], B = Phys.Indices[t + 1], C = Phys.Indices[t + 2];
				const FVector3f N = FVector3f::CrossProduct(Phys.Vertices[B] - Phys.Vertices[A], Phys.Vertices[C] - Phys.Vertices[A]);
				Smooth[A] += N; Smooth[B] += N; Smooth[C] += N;
			}
			double Agree = 0.0;
			for (int32 i = 0; i < NumVerts; ++i)
			{
				Smooth[i] = Smooth[i].GetSafeNormal();
				Agree += FVector3f::DotProduct(Smooth[i], Phys.Normals[i]);
			}
			for (int32 i = 0; i < NumVerts; ++i)
			{
				if (!Smooth[i].IsNearlyZero())
				{
					Phys.Normals[i] = Agree < 0.0 ? -Smooth[i] : Smooth[i];
				}
			}
			FPointWeightMap& DistMap = ClothLod.PointWeightMaps.AddDefaulted_GetRef();
			FPointWeightMap& RadiusMap = ClothLod.PointWeightMaps.AddDefaulted_GetRef();
			DistMap.Initialize(NumVerts);
			DistMap.Name = TEXT("BackstopDistance");
			DistMap.CurrentTarget = (uint8)EWeightMapTargetCommon::BackstopDistance;
			DistMap.bEnabled = true;
			RadiusMap.Initialize(NumVerts);
			RadiusMap.Name = TEXT("BackstopRadius");
			RadiusMap.CurrentTarget = (uint8)EWeightMapTargetCommon::BackstopRadius;
			RadiusMap.bEnabled = true;
			for (int32 i = 0; i < NumVerts; ++i)
			{
				const FVector P = (FVector)Phys.Vertices[i];
				const FVector Out = FVector(P.X - Axis.X, P.Y - Axis.Y, 0.0).GetSafeNormal();
				const bool bOn = MaxMask.Values[i] > 0.1f && FVector::DotProduct((FVector)Phys.Normals[i], Out) > MinDot;
				DistMap.Values[i] = bOn ? BDist : 0.f;
				RadiusMap.Values[i] = bOn ? BRadius : 0.f;
				NumBackstop += bOn ? 1 : 0;
			}
		}
		Asset->ApplyParameterMasks(false);
		FSkeletalMeshLODModel& LODModel = Mesh->GetImportedModel()->LODModels[0];
		const int32 OriginalIndex = LODModel.Sections[Section].OriginalDataSectionIndex;
		if (!Asset->BindToSkeletalMesh(Mesh, 0, Section, 0))
		{
			return TEXT("ERROR: BindToSkeletalMesh failed");
		}
		const int32 AssetIndex = Mesh->GetMeshClothingAssets().Find(Asset);
		FSkelMeshSourceSectionUserData& UserData = LODModel.UserSectionsData.FindOrAdd(OriginalIndex);
		UserData.CorrespondClothAssetIndex = AssetIndex;
		UserData.ClothingData.AssetGuid = Asset->GetAssetGuid();
		UserData.ClothingData.AssetLodIndex = 0;
		Asset->CalculateReferenceBoneIndex();
		Result = FString::Printf(TEXT("ok %s section=%d sim_section=%d verts=%d fixed=%d maxdist=%.2f backstop=%d asset_index=%d bones=%d"),
			*Asset->GetName(), Section, SimSection, NumVerts, NumFixed, MaxSeen, NumBackstop, AssetIndex, Asset->UsedBoneNames.Num());
	}
	Mesh->MarkPackageDirty();
	return Result;
}

int32 UPBZModToolsLibrary::RemoveAllClothing(USkeletalMesh* Mesh)
{
	if (!Mesh)
	{
		return 0;
	}
	Mesh->Modify();
	TArray<TObjectPtr<UClothingAssetBase>> Assets = Mesh->GetMeshClothingAssets();
	for (UClothingAssetBase* Asset : Assets)
	{
		if (Asset)
		{
			Asset->UnbindFromSkeletalMesh(Mesh);
		}
	}
	Mesh->GetMeshClothingAssets().Empty();
	Mesh->PostEditChange();
	Mesh->MarkPackageDirty();
	return Assets.Num();
}

int32 UPBZModToolsLibrary::SetSectionCastShadow(USkeletalMesh* Mesh, const FString& Slot, bool bCastShadow)
{
	if (!Mesh || !Mesh->GetImportedModel())
	{
		return -1;
	}
	int32 Count = 0;
	{
		FScopedSkeletalMeshPostEditChange ScopedPostEditChange(Mesh);
		Mesh->Modify();
		const TArray<FSkeletalMaterial>& Mats = Mesh->GetMaterials();
		for (FSkeletalMeshLODModel& Lod : Mesh->GetImportedModel()->LODModels)
		{
			for (FSkelMeshSection& Section : Lod.Sections)
			{
				if (Mats.IsValidIndex(Section.MaterialIndex) && Mats[Section.MaterialIndex].MaterialSlotName.ToString() == Slot)
				{
					// the user section data is what survives the next LOD rebuild
					Section.bCastShadow = bCastShadow;
					Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex).bCastShadow = bCastShadow;
					++Count;
				}
			}
		}
	}
	Mesh->MarkPackageDirty();
	return Count;
}

int32 UPBZModToolsLibrary::SetClothSolver(USkeletalMesh* Mesh, int32 Iterations, int32 Substeps)
{
	if (!Mesh)
	{
		return 0;
	}
	int32 Count = 0;
	for (UClothingAssetBase* Base : Mesh->GetMeshClothingAssets())
	{
		UClothingAssetCommon* Asset = Cast<UClothingAssetCommon>(Base);
		UChaosClothSharedSimConfig* Shared = Asset ? Asset->GetClothConfig<UChaosClothSharedSimConfig>() : nullptr;
		if (!Shared)
		{
			continue;
		}
		Shared->Modify();
		Shared->IterationCount = FMath::Max(Iterations, 1);
		Shared->SubdivisionCount = FMath::Max(Substeps, 1);
		++Count;
	}
	if (Count > 0)
	{
		Mesh->MarkPackageDirty();
	}
	return Count;
}

FString UPBZModToolsLibrary::CopyMorphTangents(USkeletalMesh* Src, USkeletalMesh* Dst)
{
	if (!Src || !Dst || !Src->GetImportedModel() || !Dst->GetImportedModel() || Src->GetImportedModel()->LODModels.Num() == 0
		|| Dst->GetImportedModel()->LODModels.Num() == 0)
	{
		return TEXT("ERROR: bad arguments");
	}
	TArray<FSoftSkinVertex> SrcVerts, DstVerts;
	Src->GetImportedModel()->LODModels[0].GetVertices(SrcVerts);
	Dst->GetImportedModel()->LODModels[0].GetVertices(DstVerts);
	if (SrcVerts.Num() != DstVerts.Num())
	{
		return FString::Printf(TEXT("ERROR: vertex count %d vs %d"), SrcVerts.Num(), DstVerts.Num());
	}
	int32 UVMismatch = 0;
	for (int32 i = 0; i < SrcVerts.Num(); ++i)
	{
		UVMismatch += SrcVerts[i].UVs[0].Equals(DstVerts[i].UVs[0], 1e-5f) ? 0 : 1;
	}
	if (UVMismatch > 0)
	{
		return FString::Printf(TEXT("ERROR: %d of %d vertices differ in UV0"), UVMismatch, SrcVerts.Num());
	}
	int32 Morphs = 0, Copied = 0, Zeroed = 0;
	for (UMorphTarget* M : Dst->GetMorphTargets())
	{
		UMorphTarget* S = M ? Src->FindMorphTarget(M->GetFName()) : nullptr;
		if (!S || S->GetMorphLODModels().Num() == 0 || M->GetMorphLODModels().Num() == 0)
		{
			continue;
		}
		TMap<uint32, FVector3f> SrcTangents;
		for (const FMorphTargetDelta& D : S->GetMorphLODModels()[0].Vertices)
		{
			SrcTangents.Add(D.SourceIdx, D.TangentZDelta);
		}
		for (FMorphTargetDelta& D : M->GetMorphLODModels()[0].Vertices)
		{
			if (const FVector3f* T = SrcTangents.Find(D.SourceIdx))
			{
				D.TangentZDelta = *T;
				++Copied;
			}
			else
			{
				D.TangentZDelta = FVector3f::ZeroVector;
				++Zeroed;
			}
		}
		M->MarkPackageDirty();
		++Morphs;
	}
	Dst->MarkPackageDirty();
	return FString::Printf(TEXT("ok morphs=%d copied=%d zeroed=%d verts=%d"), Morphs, Copied, Zeroed, DstVerts.Num());
}

FString UPBZModToolsLibrary::DumpMorphTargets(USkeletalMesh* Mesh)
{
	if (!Mesh)
	{
		return TEXT("{}");
	}
	FString Out = TEXT("{");
	int32 n = 0;
	for (const UMorphTarget* M : Mesh->GetMorphTargets())
	{
		if (!M || M->GetMorphLODModels().Num() == 0)
		{
			continue;
		}
		const FMorphTargetLODModel& Lod = M->GetMorphLODModels()[0];
		double MaxPos = 0.0, MaxN = 0.0, SumN = 0.0;
		int32 Big = 0;
		for (const FMorphTargetDelta& D : Lod.Vertices)
		{
			const double N = D.TangentZDelta.Size();
			MaxPos = FMath::Max(MaxPos, (double)D.PositionDelta.Size());
			MaxN = FMath::Max(MaxN, N);
			SumN += N;
			Big += N > 0.5 ? 1 : 0;
		}
		Out += FString::Printf(TEXT("%s\"%s\":{\"deltas\":%d,\"max_pos\":%.3f,\"max_n\":%.3f,\"mean_n\":%.3f,\"n_over_half\":%d}"),
			n++ ? TEXT(",") : TEXT(""), *M->GetName(), Lod.Vertices.Num(), MaxPos, MaxN, Lod.Vertices.Num() ? SumN / Lod.Vertices.Num() : 0.0, Big);
	}
	return Out + TEXT("}");
}

FString UPBZModToolsLibrary::SetCurveSequence(UAnimSequence* Sequence, float Length, const FString& CurvesJson)
{
	TSharedPtr<FJsonObject> Curves = ParseJson(CurvesJson);
	if (!Sequence || !Curves.IsValid() || Length <= 0.f)
	{
		return TEXT("ERROR: bad arguments");
	}
	// curves only, no bone tracks: 30 fps, smooth keys with flat tangents (no overshoot past the key values)
	IAnimationDataController& Controller = Sequence->GetController();
	Controller.OpenBracket(FText::FromString(TEXT("PBZ curve sequence")), false);
	Controller.InitializeModel();
	Controller.RemoveAllCurvesOfType(ERawCurveTrackTypes::RCT_Float, false);
	Controller.SetFrameRate(FFrameRate(30, 1), false);
	Controller.SetNumberOfFrames(FFrameNumber(FMath::RoundToInt32(Length * 30.f)), false);
	int32 NumKeys = 0;
	for (const TPair<FString, TSharedPtr<FJsonValue>>& Curve : Curves->Values)
	{
		const FAnimationCurveIdentifier Id(FName(*Curve.Key), ERawCurveTrackTypes::RCT_Float);
		Controller.AddCurve(Id, AACF_DefaultCurve, false);
		TArray<FRichCurveKey> Keys;
		for (const TSharedPtr<FJsonValue>& K : Curve.Value->AsArray())
		{
			const TArray<TSharedPtr<FJsonValue>>& TV = K->AsArray();
			FRichCurveKey& Key = Keys.Emplace_GetRef((float)TV[0]->AsNumber(), (float)TV[1]->AsNumber());
			Key.InterpMode = RCIM_Cubic;
			Key.TangentMode = RCTM_User;
			Key.ArriveTangent = Key.LeaveTangent = 0.f;
		}
		NumKeys += Keys.Num();
		Controller.SetCurveKeys(Id, Keys, false);
	}
	Controller.NotifyPopulated();
	Controller.CloseBracket(false);
	Sequence->MarkPackageDirty();
	return FString::Printf(TEXT("ok %s length=%.2f curves=%d keys=%d"), *Sequence->GetName(), Sequence->GetPlayLength(), Curves->Values.Num(), NumKeys);
}

FString UPBZModToolsLibrary::BuildCopyPoseOverlayAnimBP(UAnimBlueprint* AnimBP, UAnimSequence* Overlay, const FString& GateClass,
	const FString& SlotName, const FString& SlotRootBone, UAnimSequence* Always)
{
	if (!AnimBP || !Overlay)
	{
		return TEXT("ERROR: bad arguments");
	}
	UEdGraph* Graph = nullptr;
	for (UEdGraph* G : AnimBP->FunctionGraphs)
	{
		if (G && G->GetFName() == UEdGraphSchema_K2::GN_AnimGraph)
		{
			Graph = G;
		}
	}
	if (!Graph)
	{
		return TEXT("ERROR: no AnimGraph");
	}
	UAnimGraphNode_Root* Root = nullptr;
	for (UEdGraphNode* N : TArray<UEdGraphNode*>(Graph->Nodes))
	{
		if (UAnimGraphNode_Root* R = Cast<UAnimGraphNode_Root>(N))
		{
			Root = R;
		}
		else
		{
			Graph->RemoveNode(N);
		}
	}
	if (!Root)
	{
		return TEXT("ERROR: no root node");
	}
	// Same pose copy as the game's Hun_CopyPose (attached parent, curves and attributes, from "root"), then the overlay's
	// curves on top: layered blend without branch filters keeps every bone of the copied pose and takes the larger of
	// the two values per curve, so the overlay closes the eyes without cancelling animated expressions.
	auto MakeCopy = [Graph](int32 X, int32 Y)
	{
		FGraphNodeCreator<UAnimGraphNode_CopyPoseFromMesh> CopyCreator(*Graph);
		UAnimGraphNode_CopyPoseFromMesh* C = CopyCreator.CreateNode();
		C->Node.bUseAttachedParent = true;
		C->Node.bCopyCurves = true;
		C->Node.bCopyCustomAttributes = true;
		C->Node.bUseMeshPose = false;
		C->Node.RootBoneToCopy = TEXT("root");
		C->NodePosX = X; C->NodePosY = Y;
		CopyCreator.Finalize();
		return C;
	};
	UAnimGraphNode_CopyPoseFromMesh* Copy = MakeCopy(Root->NodePosX - 900, Root->NodePosY);
	FGraphNodeCreator<UAnimGraphNode_SequencePlayer> SeqCreator(*Graph);
	UAnimGraphNode_SequencePlayer* Seq = SeqCreator.CreateNode();
	Seq->Node.SetSequence(Overlay);
	Seq->Node.SetLoopAnimation(true);
	Seq->NodePosX = Root->NodePosX - 900; Seq->NodePosY = Root->NodePosY + 250;
	SeqCreator.Finalize();
	FGraphNodeCreator<UAnimGraphNode_LayeredBoneBlend> BlendCreator(*Graph);
	UAnimGraphNode_LayeredBoneBlend* Blend = BlendCreator.CreateNode();
	Blend->Node.CurveBlendOption = ECurveBlendOption::UseMaxValue;
	Blend->NodePosX = Root->NodePosX - 400; Blend->NodePosY = Root->NodePosY;
	BlendCreator.Finalize();
	if (Blend->Node.BlendPoses.Num() == 0)
	{
		Blend->AddPinToBlendByFilter();
	}
	for (FInputBlendPose& Layer : Blend->Node.LayerSetup)
	{
		Layer.BranchFilters.Reset();
	}
	auto PinNames = [](const UEdGraphNode* N)
	{
		FString S;
		for (const UEdGraphPin* P : N->Pins)
		{
			S += FString::Printf(TEXT("%s%s(%s) "), P->Direction == EGPD_Input ? TEXT("in:") : TEXT("out:"), *P->PinName.ToString(), *P->DefaultValue);
		}
		return S;
	};
	const UEdGraphSchema* Schema = Graph->GetSchema();
	UEdGraphPin* BaseOut = Copy->FindPin(TEXT("Pose"), EGPD_Output);
	if (!SlotName.IsEmpty())
	{
		UAnimGraphNode_CopyPoseFromMesh* SlotCopy = MakeCopy(Root->NodePosX - 1700, Root->NodePosY - 300);
		FGraphNodeCreator<UAnimGraphNode_Slot> SlotCreator(*Graph);
		UAnimGraphNode_Slot* Slot = SlotCreator.CreateNode();
		Slot->Node.SlotName = FName(*SlotName);
		Slot->NodePosX = Root->NodePosX - 1300; Slot->NodePosY = Root->NodePosY - 300;
		SlotCreator.Finalize();
		FGraphNodeCreator<UAnimGraphNode_LayeredBoneBlend> SlotBlendCreator(*Graph);
		UAnimGraphNode_LayeredBoneBlend* SlotBlend = SlotBlendCreator.CreateNode();
		SlotBlend->NodePosX = Root->NodePosX - 650; SlotBlend->NodePosY = Root->NodePosY - 150;
		SlotBlendCreator.Finalize();
		if (SlotBlend->Node.BlendPoses.Num() == 0)
		{
			SlotBlend->AddPinToBlendByFilter();
		}
		for (FInputBlendPose& Layer : SlotBlend->Node.LayerSetup)
		{
			Layer.BranchFilters.Reset();
			FBranchFilter Filter;
			Filter.BoneName = FName(*SlotRootBone);
			Filter.BlendDepth = 0;
			Layer.BranchFilters.Add(Filter);
		}
		const TPair<UEdGraphPin*, UEdGraphPin*> SlotLinks[] = {
			{SlotCopy->FindPin(TEXT("Pose"), EGPD_Output), Slot->FindPin(TEXT("Source"), EGPD_Input)},
			{BaseOut, SlotBlend->FindPin(TEXT("BasePose"), EGPD_Input)},
			{Slot->FindPin(TEXT("Pose"), EGPD_Output), SlotBlend->FindPin(TEXT("BlendPoses_0"), EGPD_Input)},
		};
		for (const TPair<UEdGraphPin*, UEdGraphPin*>& L : SlotLinks)
		{
			if (!L.Key || !L.Value || !Schema->TryCreateConnection(L.Key, L.Value))
			{
				return FString::Printf(TEXT("ERROR: slot link failed; slot [%s] blend [%s]"), *PinNames(Slot), *PinNames(SlotBlend));
			}
		}
		BaseOut = SlotBlend->FindPin(TEXT("Pose"), EGPD_Output);
	}
	UEdGraphPin* FinalOut = Blend->FindPin(TEXT("Pose"), EGPD_Output);
	if (Always)
	{
		FGraphNodeCreator<UAnimGraphNode_SequencePlayer> AlwaysSeqCreator(*Graph);
		UAnimGraphNode_SequencePlayer* AlwaysSeq = AlwaysSeqCreator.CreateNode();
		AlwaysSeq->Node.SetSequence(Always);
		AlwaysSeq->Node.SetLoopAnimation(true);
		AlwaysSeq->NodePosX = Root->NodePosX - 400; AlwaysSeq->NodePosY = Root->NodePosY + 400;
		AlwaysSeqCreator.Finalize();
		FGraphNodeCreator<UAnimGraphNode_LayeredBoneBlend> AlwaysBlendCreator(*Graph);
		UAnimGraphNode_LayeredBoneBlend* AlwaysBlend = AlwaysBlendCreator.CreateNode();
		AlwaysBlend->Node.CurveBlendOption = ECurveBlendOption::UseMaxValue;
		AlwaysBlend->NodePosX = Root->NodePosX - 200; AlwaysBlend->NodePosY = Root->NodePosY;
		AlwaysBlendCreator.Finalize();
		if (AlwaysBlend->Node.BlendPoses.Num() == 0)
		{
			AlwaysBlend->AddPinToBlendByFilter();
		}
		for (FInputBlendPose& Layer : AlwaysBlend->Node.LayerSetup)
		{
			Layer.BranchFilters.Reset();
		}
		const TPair<UEdGraphPin*, UEdGraphPin*> AlwaysLinks[] = {
			{FinalOut, AlwaysBlend->FindPin(TEXT("BasePose"), EGPD_Input)},
			{AlwaysSeq->FindPin(TEXT("Pose"), EGPD_Output), AlwaysBlend->FindPin(TEXT("BlendPoses_0"), EGPD_Input)},
		};
		for (const TPair<UEdGraphPin*, UEdGraphPin*>& L : AlwaysLinks)
		{
			if (!L.Key || !L.Value || !Schema->TryCreateConnection(L.Key, L.Value))
			{
				return FString::Printf(TEXT("ERROR: always link failed; blend [%s]"), *PinNames(AlwaysBlend));
			}
		}
		FinalOut = AlwaysBlend->FindPin(TEXT("Pose"), EGPD_Output);
	}
	const TPair<UEdGraphPin*, UEdGraphPin*> Links[] = {
		{BaseOut, Blend->FindPin(TEXT("BasePose"), EGPD_Input)},
		{Seq->FindPin(TEXT("Pose"), EGPD_Output), Blend->FindPin(TEXT("BlendPoses_0"), EGPD_Input)},
		{FinalOut, Root->FindPin(TEXT("Result"), EGPD_Input)},
	};
	for (const TPair<UEdGraphPin*, UEdGraphPin*>& L : Links)
	{
		if (!L.Key || !L.Value || !Schema->TryCreateConnection(L.Key, L.Value))
		{
			return FString::Printf(TEXT("ERROR: link failed; copy [%s] seq [%s] blend [%s] root [%s]"), *PinNames(Copy), *PinNames(Seq), *PinNames(Blend), *PinNames(Root));
		}
	}
	FString Gate = TEXT("none");
	if (!GateClass.IsEmpty())
	{
		// The same class runs on the gameplay and the cutscene components; only those of the named actor classes get the
		// overlay. The weight is decided once per anim instance from the owning actor's class name.
		const FName VarName(TEXT("KarinBlinkWeight"));
		if (FBlueprintEditorUtils::FindNewVariableIndex(AnimBP, VarName) == INDEX_NONE)
		{
			FEdGraphPinType VarType;
			VarType.PinCategory = UEdGraphSchema_K2::PC_Real;
			VarType.PinSubCategory = UEdGraphSchema_K2::PC_Double;
			FBlueprintEditorUtils::AddMemberVariable(AnimBP, VarName, VarType, TEXT("0.0"));
		}
		UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(AnimBP);
		if (!EventGraph)
		{
			return TEXT("ERROR: no EventGraph");
		}
		for (UEdGraphNode* N : TArray<UEdGraphNode*>(EventGraph->Nodes))
		{
			EventGraph->RemoveNode(N);
		}
		FGraphNodeCreator<UK2Node_Event> EvCreator(*EventGraph);
		UK2Node_Event* Ev = EvCreator.CreateNode();
		Ev->EventReference.SetExternalMember(GET_FUNCTION_NAME_CHECKED(UAnimInstance, BlueprintInitializeAnimation), UAnimInstance::StaticClass());
		Ev->bOverrideFunction = true;
		EvCreator.Finalize();
		Ev->SetEnabledState(ENodeEnabledState::Enabled, false);
		auto Call = [EventGraph](UClass* Class, const TCHAR* Name, int32 X, int32 Y) -> UK2Node_CallFunction*
		{
			UFunction* F = Class->FindFunctionByName(Name);
			if (!F)
			{
				return nullptr;
			}
			FGraphNodeCreator<UK2Node_CallFunction> C(*EventGraph);
			UK2Node_CallFunction* N = C.CreateNode();
			N->SetFromFunction(F);
			N->NodePosX = X; N->NodePosY = Y;
			C.Finalize();
			return N;
		};
		UK2Node_CallFunction* GetActor = Call(UAnimInstance::StaticClass(), TEXT("GetOwningActor"), 0, 200);
		UK2Node_CallFunction* GetClass = Call(UGameplayStatics::StaticClass(), TEXT("GetObjectClass"), 200, 200);
		UK2Node_CallFunction* ClassName = Call(UKismetSystemLibrary::StaticClass(), TEXT("GetClassDisplayName"), 400, 200);
		UK2Node_CallFunction* HasName = Call(UKismetStringLibrary::StaticClass(), TEXT("Contains"), 600, 200);
		UK2Node_CallFunction* ToDouble = Call(UKismetMathLibrary::StaticClass(), TEXT("Conv_BoolToDouble"), 800, 200);
		const bool bInvert = GateClass.StartsWith(TEXT("!"));
		UK2Node_CallFunction* Invert = bInvert ? Call(UKismetMathLibrary::StaticClass(), TEXT("Not_PreBool"), 700, 300) : nullptr;
		if (!GetActor || !GetClass || !ClassName || !HasName || !ToDouble || (bInvert && !Invert))
		{
			return TEXT("ERROR: missing function for the gate");
		}
		FGraphNodeCreator<UK2Node_VariableSet> SetCreator(*EventGraph);
		UK2Node_VariableSet* Set = SetCreator.CreateNode();
		Set->VariableReference.SetSelfMember(VarName);
		Set->NodePosX = 900; Set->NodePosY = 0;
		SetCreator.Finalize();
		const UEdGraphSchema_K2* K2 = GetDefault<UEdGraphSchema_K2>();
		UEdGraphPin* SubPin = HasName->FindPin(TEXT("Substring"), EGPD_Input);
		if (SubPin)
		{
			K2->TrySetDefaultValue(*SubPin, bInvert ? GateClass.Mid(1) : GateClass);
		}
		UEdGraphPin* Test = HasName->GetReturnValuePin();
		if (Invert)
		{
			if (!K2->TryCreateConnection(Test, Invert->FindPin(TEXT("A"), EGPD_Input)))
			{
				return FString::Printf(TEXT("ERROR: gate link failed; not [%s]"), *PinNames(Invert));
			}
			Test = Invert->GetReturnValuePin();
		}
		const TPair<UEdGraphPin*, UEdGraphPin*> GateLinks[] = {
			{Ev->FindPin(UEdGraphSchema_K2::PN_Then, EGPD_Output), Set->GetExecPin()},
			{GetActor->GetReturnValuePin(), GetClass->FindPin(TEXT("Object"), EGPD_Input)},
			{GetClass->GetReturnValuePin(), ClassName->FindPin(TEXT("Class"), EGPD_Input)},
			{ClassName->GetReturnValuePin(), HasName->FindPin(TEXT("SearchIn"), EGPD_Input)},
			{Test, ToDouble->FindPin(TEXT("InBool"), EGPD_Input)},
			{ToDouble->GetReturnValuePin(), Set->FindPin(VarName, EGPD_Input)},
		};
		for (const TPair<UEdGraphPin*, UEdGraphPin*>& L : GateLinks)
		{
			if (!SubPin || !L.Key || !L.Value || !K2->TryCreateConnection(L.Key, L.Value))
			{
				return FString::Printf(TEXT("ERROR: gate link failed; event [%s] actor [%s] class [%s] name [%s] contains [%s] conv [%s] set [%s]"),
					*PinNames(Ev), *PinNames(GetActor), *PinNames(GetClass), *PinNames(ClassName), *PinNames(HasName), *PinNames(ToDouble), *PinNames(Set));
			}
		}
		FGraphNodeCreator<UK2Node_VariableGet> GetCreator(*Graph);
		UK2Node_VariableGet* Weight = GetCreator.CreateNode();
		Weight->VariableReference.SetSelfMember(VarName);
		Weight->NodePosX = Root->NodePosX - 700; Weight->NodePosY = Root->NodePosY + 450;
		GetCreator.Finalize();
		UEdGraphPin* WeightPin = Blend->FindPin(TEXT("BlendWeights_0"), EGPD_Input);
		if (!WeightPin || !Schema->TryCreateConnection(Weight->FindPin(VarName, EGPD_Output), WeightPin))
		{
			return FString::Printf(TEXT("ERROR: weight link failed; get [%s] blend [%s]"), *PinNames(Weight), *PinNames(Blend));
		}
		Gate = GateClass;
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);
	FKismetEditorUtilities::CompileBlueprint(AnimBP, EBlueprintCompileOptions::SkipGarbageCollection);
	AnimBP->MarkPackageDirty();
	return FString::Printf(TEXT("%s status=%d poses=%d layers=%d gate=%s slot=%s/%s always=%s blend [%s]"), AnimBP->Status == BS_Error ? TEXT("ERROR: compile") : TEXT("ok"),
		(int32)AnimBP->Status, Blend->Node.BlendPoses.Num(), Blend->Node.LayerSetup.Num(), *Gate, *SlotName, *SlotRootBone,
		Always ? *Always->GetName() : TEXT("none"), *PinNames(Blend));
}

FString UPBZModToolsLibrary::TestCopyPoseAnim(UClass* AnimClass, USkeletalMesh* Mesh, float Seconds, int32 Steps, const FString& Curve)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!AnimClass || !Mesh || !World || Steps <= 0)
	{
		return TEXT("ERROR: bad arguments or no editor world");
	}
	AActor* Actor = World->SpawnActor<AActor>();
	if (!Actor)
	{
		return TEXT("ERROR: spawn failed");
	}
	USkeletalMeshComponent* Comp = NewObject<USkeletalMeshComponent>(Actor, TEXT("TestMesh"));
	Comp->SetUpdateAnimationInEditor(true);
	Comp->SetSkeletalMeshAsset(Mesh);
	Comp->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	Comp->SetAnimInstanceClass(AnimClass);
	Actor->SetRootComponent(Comp);
	Comp->RegisterComponent();
	Comp->InitAnim(true);
	UAnimInstance* Inst = Comp->GetAnimInstance();
	FString Result;
	if (!Inst)
	{
		Result = TEXT("ERROR: no anim instance");
	}
	else
	{
		const float Dt = Seconds / Steps;
		for (int32 i = 0; i < Steps; ++i)
		{
			Comp->TickAnimation(Dt, false);
			Comp->RefreshBoneTransforms();
			Comp->HandleExistingParallelEvaluationTask(true, true);
		}
		double Weight = -1.0;
		if (const FDoubleProperty* P = FindFProperty<FDoubleProperty>(Inst->GetClass(), TEXT("KarinBlinkWeight")))
		{
			Weight = P->GetPropertyValue_InContainer(Inst);
		}
		Result = FString::Printf(TEXT("{\"actor_class\": \"%s\", \"anim\": \"%s\", \"weight\": %.3f, \"curve\": %.3f, \"morph\": %.3f}"),
			*Actor->GetClass()->GetName(), *Inst->GetClass()->GetName(), Weight, Inst->GetCurveValue(FName(*Curve)), Comp->GetMorphTarget(FName(*Curve)));
	}
	Actor->Destroy();
	return Result;
}
